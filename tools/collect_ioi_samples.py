import argparse
import csv
import statistics
import time
from pathlib import Path
import tkinter as tk


WINDOW_TITLE = "Tap Collector"
INSTRUCTIONS = (
    "Press SPACE to tap\n"
    "Press ENTER to save and quit\n"
    "Press ESC to quit without saving\n"
)

MIN_TAPS_REQUIRED = 2
NS_PER_MS = 1_000_000


class TapCollectorApp:
    def __init__(self, output_path: Path, target_taps: int | None) -> None:
        self.output_path = output_path
        self.target_taps = target_taps
        self.timestamps_ns: list[int] = []
        self.space_is_down = False
        self.num_timestamps = 0

        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry("700x320")
        self.root.configure(padx=20, pady=20)

        self.status_var = tk.StringVar()
        self.summary_var = tk.StringVar()

        title = tk.Label(self.root, text="Inter-Onset Interval Collector", font=("Arial", 18, "bold"))
        title.pack(pady=(0, 12))

        instructions = tk.Label(self.root, text=INSTRUCTIONS, font=("Arial", 16))
        instructions.pack(pady=(0, 8))

        status = tk.Label(self.root, textvariable=self.status_var, font=("Arial", 16))
        status.pack(pady=(0, 8))

        summary = tk.Label(self.root, textvariable=self.summary_var, font=("Arial, 12"), justify="center")
        summary.pack()

        self.root.bind("<KeyPress-space>", self.on_space_press)
        self.root.bind("<KeyRelease-space>", self.on_space_release)
        self.root.bind("<Return>", self.on_save_and_quit)
        self.root.bind("<Escape>", self.on_quit_without_saving)

        self.refresh()

    def on_space_press(self, event) -> None:
        if self.space_is_down:
            return

        self.space_is_down = True
        self.timestamps_ns.append(time.perf_counter_ns())
        self.num_timestamps += 1
        self.refresh()

        if self.target_taps is not None and self.num_timestamps >= self.target_taps:
            self.save()
            self.root.destroy()

    def on_space_release(self, event) -> None:
        self.space_is_down = False

    def on_save_and_quit(self, event) -> None:
        if self.num_timestamps < MIN_TAPS_REQUIRED:
            self.status_var.set("Need at least 2 taps before saving")
            return

        self.save()
        self.root.destroy()

    def on_quit_without_saving(self, event) -> None:
        self.root.destroy()

    def refresh(self) -> None:
        self.status_var.set(f"Taps recorded: {self.num_timestamps}")

        if self.num_timestamps < MIN_TAPS_REQUIRED:
            self.summary_var.set("No IOIs yet")
            return

        iois_ms = compute_iois_ms(self.timestamps_ns, self.num_timestamps)
        mean_ioi = statistics.mean(iois_ms)
        std_ioi = statistics.stdev(iois_ms) if self.num_timestamps > MIN_TAPS_REQUIRED else 0.0

        self.summary_var.set(f"IOIs: {len(iois_ms)} | Mean: {mean_ioi:.2f} ms | Std: {std_ioi:.2f} ms")

    def save(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True) 

        with self.output_path.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["tap_index", "timestamp_ns", "timestamp_ms_from_start", "ioi_ms"])
            start_ns = self.timestamps_ns[0]

            for index, timestamp_ns in enumerate(self.timestamps_ns):
                timestamp_ns_from_start = (timestamp_ns - start_ns) / NS_PER_MS
                ioi_ms = ""
                if index > 0:
                    ioi_ms = (timestamp_ns - self.timestamps_ns[index - 1]) / NS_PER_MS

                writer.writerow([index, timestamp_ns, f"{timestamp_ns_from_start:.3f}", ioi_ms])

            print(f"Saved tap data to {self.output_path}")


def compute_iois_ms(timestamps_ns: list[int], num_timestamps: int) -> list[float]:
    return [
        (timestamps_ns[index] - timestamps_ns[index - 1]) / NS_PER_MS
        for index in range(1, num_timestamps)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect tap timestamps from the keyboard")
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output CSV path"
    )
    parser.add_argument(
        "--target-taps",
        type=int,
        default=121,
        help="Automatically save after this many taps. Default: 121"
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = TapCollectorApp(output_path=args.out, target_taps=args.target_taps)
    app.root.mainloop()


if __name__ == "__main__":
    main()

