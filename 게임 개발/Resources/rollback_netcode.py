"""A minimal rollback simulation with delayed remote inputs."""

from dataclasses import dataclass


@dataclass(frozen=True)
class State:
    local_position: int
    remote_position: int


def advance(state: State, local_input: int, remote_input: int) -> State:
    return State(
        state.local_position + local_input,
        state.remote_position + remote_input,
    )


def simulate() -> None:
    local_inputs = [1, 1, 0, -1, -1, 0, 1, 1]
    actual_remote_inputs = [0, 1, 1, 1, 0, -1, -1, 0]
    delay = 3
    known_remote: dict[int, int] = {}
    predicted_remote: dict[int, int] = {}
    state_history: dict[int, State] = {0: State(0, 0)}
    state = state_history[0]

    for frame in range(len(local_inputs)):
        arrived_frame = frame - delay
        if arrived_frame >= 0:
            actual = actual_remote_inputs[arrived_frame]
            known_remote[arrived_frame] = actual
            predicted = predicted_remote[arrived_frame]
            if predicted != actual:
                state = state_history[arrived_frame]
                for replay_frame in range(arrived_frame, frame):
                    remote = known_remote.get(
                        replay_frame,
                        predicted_remote[replay_frame],
                    )
                    state = advance(
                        state,
                        local_inputs[replay_frame],
                        remote,
                    )
                    state_history[replay_frame + 1] = state
                print(f"rollback frame={arrived_frame}, replayed_to={frame}")

        last_known = known_remote.get(frame - 1, 0)
        predicted_remote[frame] = known_remote.get(frame, last_known)
        state_history[frame] = state
        state = advance(state, local_inputs[frame], predicted_remote[frame])
        state_history[frame + 1] = state
        print(f"frame={frame} state={state}")


if __name__ == "__main__":
    simulate()
