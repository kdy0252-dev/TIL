"""A minimal decoder-only Transformer that can run on CPU or NVIDIA CUDA."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as functional


@dataclass(frozen=True)
class Config:
    context_length: int = 64
    embedding_dim: int = 128
    num_heads: int = 4
    num_layers: int = 4
    dropout: float = 0.1


class CausalSelfAttention(nn.Module):
    def __init__(self, config: Config) -> None:
        super().__init__()
        if config.embedding_dim % config.num_heads != 0:
            raise ValueError("embedding_dim must be divisible by num_heads")

        self.num_heads = config.num_heads
        self.head_dim = config.embedding_dim // config.num_heads
        self.query_key_value = nn.Linear(config.embedding_dim, 3 * config.embedding_dim)
        self.output = nn.Linear(config.embedding_dim, config.embedding_dim)
        self.dropout = config.dropout

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        batch_size, sequence_length, embedding_dim = hidden.shape
        query, key, value = self.query_key_value(hidden).chunk(3, dim=-1)

        def split_heads(tensor: torch.Tensor) -> torch.Tensor:
            return tensor.view(
                batch_size,
                sequence_length,
                self.num_heads,
                self.head_dim,
            ).transpose(1, 2)

        query, key, value = map(split_heads, (query, key, value))
        attended = functional.scaled_dot_product_attention(
            query,
            key,
            value,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=True,
        )
        attended = attended.transpose(1, 2).contiguous().view(
            batch_size,
            sequence_length,
            embedding_dim,
        )
        return self.output(attended)


class FeedForward(nn.Module):
    def __init__(self, config: Config) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(config.embedding_dim, 4 * config.embedding_dim),
            nn.GELU(),
            nn.Linear(4 * config.embedding_dim, config.embedding_dim),
            nn.Dropout(config.dropout),
        )

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        return self.layers(hidden)


class TransformerBlock(nn.Module):
    def __init__(self, config: Config) -> None:
        super().__init__()
        self.attention_norm = nn.LayerNorm(config.embedding_dim)
        self.attention = CausalSelfAttention(config)
        self.feed_forward_norm = nn.LayerNorm(config.embedding_dim)
        self.feed_forward = FeedForward(config)

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        hidden = hidden + self.attention(self.attention_norm(hidden))
        return hidden + self.feed_forward(self.feed_forward_norm(hidden))


class MiniGpt(nn.Module):
    def __init__(self, vocabulary_size: int, config: Config) -> None:
        super().__init__()
        self.config = config
        self.token_embedding = nn.Embedding(vocabulary_size, config.embedding_dim)
        self.position_embedding = nn.Embedding(config.context_length, config.embedding_dim)
        self.blocks = nn.Sequential(
            *(TransformerBlock(config) for _ in range(config.num_layers))
        )
        self.final_norm = nn.LayerNorm(config.embedding_dim)
        self.language_model_head = nn.Linear(config.embedding_dim, vocabulary_size, bias=False)
        self.language_model_head.weight = self.token_embedding.weight

    def forward(
        self,
        token_ids: torch.Tensor,
        targets: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        _, sequence_length = token_ids.shape
        if sequence_length > self.config.context_length:
            raise ValueError("sequence is longer than context_length")

        positions = torch.arange(sequence_length, device=token_ids.device)
        hidden = self.token_embedding(token_ids) + self.position_embedding(positions)
        hidden = self.final_norm(self.blocks(hidden))
        logits = self.language_model_head(hidden)

        loss = None
        if targets is not None:
            loss = functional.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                targets.reshape(-1),
            )
        return logits, loss

    @torch.no_grad()
    def generate(self, token_ids: torch.Tensor, max_new_tokens: int) -> torch.Tensor:
        for _ in range(max_new_tokens):
            context = token_ids[:, -self.config.context_length :]
            logits, _ = self(context)
            probabilities = functional.softmax(logits[:, -1, :], dim=-1)
            next_token = torch.multinomial(probabilities, num_samples=1)
            token_ids = torch.cat((token_ids, next_token), dim=1)
        return token_ids


def build_dataset() -> tuple[torch.Tensor, dict[str, int], dict[int, str]]:
    text = (
        "a language model predicts the next token from previous tokens. "
        "attention mixes information across the sequence. "
    ) * 200
    characters = sorted(set(text))
    encode_table = {character: index for index, character in enumerate(characters)}
    decode_table = {index: character for character, index in encode_table.items()}
    encoded = torch.tensor([encode_table[character] for character in text], dtype=torch.long)
    return encoded, encode_table, decode_table


def get_batch(
    data: torch.Tensor,
    batch_size: int,
    context_length: int,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    starts = torch.randint(0, len(data) - context_length - 1, (batch_size,))
    inputs = torch.stack([data[index : index + context_length] for index in starts])
    targets = torch.stack([data[index + 1 : index + context_length + 1] for index in starts])
    return inputs.to(device, non_blocking=True), targets.to(device, non_blocking=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    args = parser.parse_args()

    torch.manual_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = device.type == "cuda"
    data, encode_table, decode_table = build_dataset()
    config = Config()
    model = MiniGpt(len(encode_table), config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    print(f"device={device}, parameters={sum(p.numel() for p in model.parameters()):,}")
    model.train()
    for step in range(args.steps):
        inputs, targets = get_batch(
            data,
            args.batch_size,
            config.context_length,
            device,
        )
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(
            device_type=device.type,
            dtype=torch.float16,
            enabled=use_amp,
        ):
            _, loss = model(inputs, targets)
        if loss is None:
            raise RuntimeError("training loss was not created")
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()

        if step % 25 == 0:
            print(f"step={step:04d}, loss={loss.item():.4f}")

    model.eval()
    seed = torch.tensor([[encode_table["a"]]], device=device)
    generated = model.generate(seed, max_new_tokens=120)[0].tolist()
    print("".join(decode_table[token] for token in generated))


if __name__ == "__main__":
    main()
