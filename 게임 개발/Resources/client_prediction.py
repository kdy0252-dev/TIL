"""Client prediction and server reconciliation in a deterministic 1D world."""

from dataclasses import dataclass


DT = 1.0 / 20.0
SPEED = 4.0


@dataclass(frozen=True)
class InputCommand:
    sequence: int
    axis: float


def simulate(command_count: int = 40, one_way_delay_ticks: int = 3) -> None:
    client_position = 0.0
    server_position = 0.0
    pending: list[InputCommand] = []
    input_pipe: list[tuple[int, InputCommand]] = []
    snapshot_pipe: list[tuple[int, float, int]] = []
    last_processed = -1

    for tick in range(command_count + one_way_delay_ticks * 3):
        if tick < command_count:
            command = InputCommand(tick, 1.0 if tick < 25 else -0.5)
            pending.append(command)
            client_position += command.axis * SPEED * DT
            input_pipe.append((tick + one_way_delay_ticks, command))

        arrived = [item for item in input_pipe if item[0] == tick]
        for _, command in arrived:
            server_position += command.axis * SPEED * DT
            last_processed = command.sequence
            snapshot_pipe.append(
                (tick + one_way_delay_ticks, server_position, last_processed)
            )

        snapshots = [item for item in snapshot_pipe if item[0] == tick]
        for _, authoritative_position, acknowledged_sequence in snapshots:
            pending = [
                command
                for command in pending
                if command.sequence > acknowledged_sequence
            ]
            client_position = authoritative_position
            for command in pending:
                client_position += command.axis * SPEED * DT

        if tick % 5 == 0:
            error = client_position - server_position
            print(
                f"tick={tick:02d} client={client_position:6.3f} "
                f"server={server_position:6.3f} error={error:6.3f} "
                f"pending={len(pending)}"
            )


if __name__ == "__main__":
    simulate()
