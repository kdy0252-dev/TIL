"""Snapshot interpolation with a render-time delay buffer."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Snapshot:
    server_time: float
    position: float


def sample(snapshots: list[Snapshot], render_time: float) -> float | None:
    before = None
    after = None
    for snapshot in snapshots:
        if snapshot.server_time <= render_time:
            before = snapshot
        if snapshot.server_time >= render_time:
            after = snapshot
            break
    if before is None or after is None:
        return None
    if before.server_time == after.server_time:
        return before.position
    alpha = (render_time - before.server_time) / (
        after.server_time - before.server_time
    )
    return before.position + (after.position - before.position) * alpha


def simulate() -> None:
    snapshots = [
        Snapshot(0.0, 0.0),
        Snapshot(0.1, 0.9),
        Snapshot(0.2, 2.1),
        Snapshot(0.3, 3.0),
        Snapshot(0.4, 4.2),
    ]
    interpolation_delay = 0.1
    for frame in range(12, 31):
        local_time = frame / 60.0
        render_time = local_time - interpolation_delay
        position = sample(snapshots, render_time)
        if position is not None:
            print(
                f"local={local_time:.3f} render={render_time:.3f} "
                f"position={position:.3f}"
            )


if __name__ == "__main__":
    simulate()
