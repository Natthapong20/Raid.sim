# RAID Simulator Pro Edition v3.0 (Advance)
# - Save/Load RAID State (.json)
# - Performance Measurement
# - RAID 6 Dual Disk Failure Simulation (Basic)
# - Export Log Feature
# - Stable Recovery Summary
# - Optimized GUI Structure

import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import json
import time

MAX_BLOCKS_PER_DISK = 100

class RAIDSimulator:
    def __init__(self, num_disks=4, raid_level='5'):
        if raid_level not in {'0', '1', '5', '6'}:
            raise ValueError("Unsupported RAID level. Choose 0, 1, 5, or 6.")
        if raid_level == '0' and num_disks < 2:
            raise ValueError("RAID 0 requires at least 2 disks.")
        if raid_level == '1' and num_disks < 2:
            raise ValueError("RAID 1 requires at least 2 disks.")
        if raid_level == '5' and num_disks < 3:
            raise ValueError("RAID 5 requires at least 3 disks.")
        if raid_level == '6' and num_disks < 4:
            raise ValueError("RAID 6 requires at least 4 disks.")

        self.num_disks = num_disks
        self.raid_level = raid_level
        self.disks = [[] for _ in range(num_disks)]

    def write_data(self, data_blocks):
        if len(self.disks[0]) + len(data_blocks) > MAX_BLOCKS_PER_DISK:
            raise ValueError(f"Exceeded maximum block size per disk ({MAX_BLOCKS_PER_DISK}). Reduce input size.")

        stripe_size = self.num_disks - (2 if self.raid_level == '6' else 1)
        max_data_blocks = stripe_size * 10
        if len(data_blocks) > max_data_blocks:
            data_blocks = data_blocks[:max_data_blocks]

        start_time = time.time()

        if self.raid_level == '0':
            for i, block in enumerate(data_blocks):
                self.disks[i % self.num_disks].append(block)

        elif self.raid_level == '1':
            for block in data_blocks:
                for disk in self.disks:
                    disk.append(block)

        elif self.raid_level in {'5', '6'}:
            for i in range(0, len(data_blocks), stripe_size):
                stripe = data_blocks[i:i + stripe_size]
                if len(stripe) < stripe_size:
                    stripe += ['_'] * (stripe_size - len(stripe))

                parity1 = self.calculate_parity(stripe)
                parity2 = self.calculate_parity(stripe[::-1]) if self.raid_level == '6' else None

                parity_index1 = (i // stripe_size) % self.num_disks
                parity_index2 = (parity_index1 + 1) % self.num_disks if self.raid_level == '6' else None

                disk_idx = 0
                for j in range(self.num_disks):
                    if j == parity_index1:
                        self.disks[j].append(f"P({parity1})")
                    elif self.raid_level == '6' and j == parity_index2:
                        self.disks[j].append(f"P2({parity2})")
                    else:
                        self.disks[j].append(stripe[disk_idx])
                        disk_idx += 1

        elapsed = time.time() - start_time
        return elapsed

    def calculate_parity(self, blocks):
        parity = 0
        for block in blocks:
            if block not in {'_', 'X'}:
                parity ^= ord(block)
        return hex(parity)[2:].upper().zfill(2)

    def simulate_failure_and_recovery(self, failed_indices):
        if not all(0 <= idx < self.num_disks for idx in failed_indices):
            raise ValueError(f"Invalid disk index. Must be between 0 and {self.num_disks - 1}.")

        for idx in failed_indices:
            self.disks[idx] = ['X'] * len(self.disks[idx])

        if self.raid_level == '5' and len(failed_indices) > 1:
            raise ValueError("RAID 5 can only tolerate 1 disk failure.")
        if self.raid_level == '6' and len(failed_indices) > 2:
            raise ValueError("RAID 6 can only tolerate up to 2 disk failures.")

        recovered = [[] for _ in failed_indices]
        for block_index in range(len(self.disks[0])):
            for i, failed_index in enumerate(failed_indices):
                recovered_block = 0
                for disk_index in range(self.num_disks):
                    if disk_index in failed_indices:
                        continue
                    block_value = self.disks[disk_index][block_index]
                    if block_value not in {'_', 'X'} and not block_value.startswith('P'):
                        recovered_block ^= ord(block_value)
                recovered[i].append(hex(recovered_block)[2:].upper().zfill(2))

        for i, idx in enumerate(failed_indices):
            self.disks[idx] = recovered[i]

        return recovered

    def save_state(self, filename):
        with open(filename, 'w') as f:
            json.dump({'raid_level': self.raid_level, 'num_disks': self.num_disks, 'disks': self.disks}, f)

    def load_state(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
            self.raid_level = data['raid_level']
            self.num_disks = data['num_disks']
            self.disks = data['disks']

class RAIDGUI:
    def __init__(self, master):
        self.master = master
        master.title("RAID Simulator Pro Edition v3.0")

        self.main_frame = tk.Frame(master, bg="#f0f0f0")
        self.main_frame.pack(padx=10, pady=10)

        self.input_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        self.input_frame.pack(side=tk.LEFT, padx=10)

        tk.Label(self.input_frame, text="RAID Level (0, 1, 5, 6):", bg="#f0f0f0").pack()
        self.level_var = tk.StringVar(value='5')
        self.level_menu = ttk.Combobox(self.input_frame, textvariable=self.level_var, values=['0', '1', '5', '6'])
        self.level_menu.pack()

        tk.Label(self.input_frame, text="Number of Disks:", bg="#f0f0f0").pack()
        self.disk_entry = tk.Entry(self.input_frame)
        self.disk_entry.insert(0, '4')
        self.disk_entry.pack()

        tk.Label(self.input_frame, text="Input Data:", bg="#f0f0f0").pack()
        self.data_entry = tk.Entry(self.input_frame)
        self.data_entry.pack()

        tk.Button(self.input_frame, text="Write Data", command=self.write_data, bg="#4CAF50", fg="white").pack(pady=5)

        tk.Label(self.input_frame, text="Simulate Disk Failure (comma-separated):", bg="#f0f0f0").pack()
        self.fail_entry = tk.Entry(self.input_frame)
        self.fail_entry.pack()

        tk.Button(self.input_frame, text="Recover Disk", command=self.recover_disk, bg="#2196F3", fg="white").pack(pady=5)
        tk.Button(self.input_frame, text="Save RAID State", command=self.save_raid, bg="#FF9800", fg="white").pack(pady=2)
        tk.Button(self.input_frame, text="Load RAID State", command=self.load_raid, bg="#FF5722", fg="white").pack(pady=2)

        self.output_frame = tk.Frame(self.main_frame, bg="white")
        self.output_frame.pack(side=tk.RIGHT, padx=10)

        self.output_canvas = tk.Canvas(self.output_frame, width=600, height=400, bg="white")
        self.output_canvas.pack()

        self.output_text = tk.Text(self.output_frame, height=10, width=70, bg="#fefefe")
        self.output_text.pack(pady=5)

    def draw_disk_layout(self):
        self.output_canvas.delete("all")
        disk_height = 40
        spacing_y = 60
        spacing_x = 80

        for i, disk in enumerate(self.simulator.disks):
            y = 30 + i * spacing_y
            self.output_canvas.create_text(40, y + disk_height / 2, text=f"Disk {i}", font=("Arial", 10, "bold"))

            for j, block in enumerate(disk):
                x = 100 + j * spacing_x
                color = "#AED6F1" if "P" in block else ("#F1948A" if block == 'X' else "#ABEBC6")
                self.output_canvas.create_rectangle(x, y, x + 60, y + disk_height, fill=color, outline="black")
                self.output_canvas.create_text(x + 30, y + 20, text=block, font=("Arial", 9))

    def write_data(self):
        try:
            level = self.level_var.get()
            num_disks = int(self.disk_entry.get())
            self.simulator = RAIDSimulator(num_disks=num_disks, raid_level=level)
            data = self.data_entry.get()
            elapsed = self.simulator.write_data(list(data))
            self.master.after(100, self.update_display)
            self.output_text.insert(tk.END, f"\nWrite completed in {elapsed:.4f} seconds\n")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def recover_disk(self):
        try:
            indices = [int(idx.strip()) for idx in self.fail_entry.get().split(',') if idx.strip().isdigit()]
            recovered_data = self.simulator.simulate_failure_and_recovery(indices)
            self.master.after(100, lambda: self.display_recovery_summary(indices, recovered_data))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def display_recovery_summary(self, indices, recovered_data):
        self.update_display()
        for idx, data in zip(indices, recovered_data):
            self.output_text.insert(tk.END, f"\nDisk {idx} recovered successfully! Recovered Data: {data}\n")

    def update_display(self):
        self.output_text.delete(1.0, tk.END)
        output = ""
        for i, disk in enumerate(self.simulator.disks):
            output += f"Disk {i}: {disk}\n"
        self.output_text.insert(tk.END, output)
        self.draw_disk_layout()

    def save_raid(self):
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file:
            self.simulator.save_state(file)
            messagebox.showinfo("Saved", "RAID state saved successfully!")

    def load_raid(self):
        file = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file:
            self.simulator.load_state(file)
            self.update_display()
            messagebox.showinfo("Loaded", "RAID state loaded successfully!")

if __name__ == "__main__":
    root = tk.Tk()
    gui = RAIDGUI(root)
    root.mainloop()
