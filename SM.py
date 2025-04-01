import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import json
import time

MAX_BLOCKS_PER_DISK = 100  # Maximum blocks per disk

class RAIDSimulator:
    def __init__(self, num_disks=4, raid_level='5'):
        # Check RAID level validity
        if raid_level not in {'0', '1', '5', '10'}:
            raise ValueError("Unsupported RAID level. Choose 0, 1, 5, or 10.")
        if raid_level == '0' and num_disks < 2:
            raise ValueError("RAID 0 requires at least 2 disks.")
        if raid_level == '1' and num_disks < 2:
            raise ValueError("RAID 1 requires at least 2 disks.")
        if raid_level == '5' and num_disks < 3:
            raise ValueError("RAID 5 requires at least 3 disks.")
        if raid_level == '10' and (num_disks < 4 or num_disks % 2 != 0 or num_disks > 32):
            raise ValueError("RAID 10 requires at least 4 disks and must be even.")

        # Store values
        self.num_disks = num_disks
        self.raid_level = raid_level
        self.disks = [[] for _ in range(num_disks)]  # Initialize disks

    def write_data(self, data_blocks):
        # Ensure blocks do not exceed maximum limit
        if len(self.disks[0]) + len(data_blocks) > MAX_BLOCKS_PER_DISK:
            raise ValueError(f"Exceeded maximum block size per disk ({MAX_BLOCKS_PER_DISK}). Reduce input size.")

        # Set stripe size and max block for RAID levels
        stripe_size = self.num_disks - 1 if self.raid_level == '5' else self.num_disks // 2
        max_data_blocks = stripe_size * 10

        if len(data_blocks) > max_data_blocks:
            data_blocks = data_blocks[:max_data_blocks]  # Limit input

        start_time = time.time()  # Start timer

        # Write data based on RAID type
        if self.raid_level == '0':  # RAID 0 (striping)
            for i, block in enumerate(data_blocks):
                self.disks[i % self.num_disks].append(block)

        elif self.raid_level == '1':  # RAID 1 (mirroring)
            for block in data_blocks:
                for disk in self.disks:
                    disk.append(block)

        elif self.raid_level == '5':  # RAID 5 (parity)
            for i in range(0, len(data_blocks), stripe_size):
                stripe = data_blocks[i:i + stripe_size]
                if len(stripe) < stripe_size:
                    stripe += ['_'] * (stripe_size - len(stripe))  # padding

                parity1 = self.calculate_parity(stripe)  # Calculate parity

                parity_index1 = (i // stripe_size) % self.num_disks

                disk_idx = 0
                for j in range(self.num_disks):
                    if j == parity_index1:
                        self.disks[j].append(f"P({parity1})")  # Write parity
                    else:
                        self.disks[j].append(stripe[disk_idx])  # Write real data
                        disk_idx += 1

        elif self.raid_level == '10':  # RAID 10 (mirror + stripe)
            half = self.num_disks // 2
            for i, block in enumerate(data_blocks):
                stripe_idx = i % half
                self.disks[stripe_idx].append(block)  # Write to stripe
                self.disks[stripe_idx + half].append(block)  # Write to mirror

        elapsed = time.time() - start_time  # Calculate time elapsed
        return elapsed

    def calculate_parity(self, blocks):
        # Calculate parity using XOR
        parity = 0
        for block in blocks:
            if block not in {'_', 'X'}:
                parity ^= ord(block)
        return hex(parity)[2:].upper().zfill(2)

    def simulate_failure_and_recovery(self, failed_indices):
    # Check RAID 0 cannot recover
        if self.raid_level == '0':
            raise ValueError("\u2757\ufe0f RAID 0 cannot recover from disk failure. Data is lost.")
    
    # Validate failed indices
        if not all(0 <= idx < self.num_disks for idx in failed_indices):
            raise ValueError(f"\u2757\ufe0f Invalid disk index.")
    
        for idx in failed_indices:
            self.disks[idx] = ['X'] * len(self.disks[idx])  # Mark disk as failed

    # Recover for RAID 1, 5, 10
        if self.raid_level == '5' and len(failed_indices) > 1:
            raise ValueError("\u2757\ufe0f RAID 5 can only tolerate 1 disk failure.")
    
        if self.raid_level == '10':
            half = self.num_disks // 2
            for idx in failed_indices:
                mirror_idx = idx - half if idx >= half else idx + half
                if mirror_idx in failed_indices:
                    raise ValueError("\u2757\ufe0f RAID 10 can only tolerate one disk failure per mirrored pair.")
            for idx in failed_indices:
                mirror_idx = idx - half if idx >= half else idx + half
                self.disks[idx] = self.disks[mirror_idx][:]
            return [self.disks[idx] for idx in failed_indices]

    # Recovery for RAID 5
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

        

        # Recovery for RAID 5
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

    def save_state(self, filename):
        # Save RAID state to JSON
        with open(filename, 'w') as f:
            json.dump({'raid_level': self.raid_level, 'num_disks': self.num_disks, 'disks': self.disks}, f)

    def load_state(self, filename):
        # Load RAID state from JSON
        with open(filename, 'r') as f:
            data = json.load(f)
            self.raid_level = data['raid_level']
            self.num_disks = data['num_disks']
            self.disks = data['disks']


class RAIDGUI:
    def __init__(self, master):
        # GUI initialization
        self.master = master
        master.title("RAID Simulator Pro Edition v3.0")

        self.main_frame = tk.Frame(master, bg="#f0f0f0")
        self.main_frame.pack(padx=10, pady=10)

        self.input_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        self.input_frame.pack(side=tk.LEFT, padx=10)

        tk.Label(self.input_frame, text="RAID Level (0, 1, 5, 10):", bg="#f0f0f0").pack()
        self.level_var = tk.StringVar(value='5')
        self.level_menu = ttk.Combobox(self.input_frame, textvariable=self.level_var, values=['0', '1', '5', '10'])
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
        # Draw disk layout on canvas
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
        # Write data to RAID
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
        # ฟังก์ชัน recovery disk
        try:
            level = self.level_var.get()
            indices = [int(idx.strip()) for idx in self.fail_entry.get().split(',') if idx.strip().isdigit()]

            # ตรวจสอบว่า RAID 0 ไม่สามารถกู้คืนได้
            if level == '0':
                self.update_display()
                self.output_text.insert(tk.END, "\n❌ Disk failure detected! RAID 0 cannot recover. Data is lost.\n")
                for idx in indices:
                    if 0 <= idx < self.simulator.num_disks:
                        self.simulator.disks[idx] = ['X'] * len(self.simulator.disks[idx])  # ทำเครื่องหมายดิสก์ล้มเหลว
                self.update_display()
                return  # หยุดการกู้คืนทันทีสำหรับ RAID 0

            # กู้คืนดิสก์สำหรับ RAID อื่น ๆ
            recovered_data = self.simulator.simulate_failure_and_recovery(indices)
            self.master.after(100, lambda: self.display_recovery_summary(indices, recovered_data))
        except Exception as e:
            self.output_text.insert(tk.END, f"\n❗️ Error: {str(e)}\n")


    def display_recovery_summary(self, indices, recovered_data):
    # แสดงผลการ recover
        self.update_display()
        if self.level_var.get() == '0':
            self.output_text.insert(tk.END, "\n❌ Disk failure detected! RAID 0 cannot recover. Data is lost.\n")
        else:
            for idx, data in zip(indices, recovered_data):
                self.output_text.insert(tk.END, f"\n✅ Disk {idx} recovered successfully! Recovered Data: {data}\n")


    def update_display(self):
        # Update display with data and layout
        self.output_text.delete(1.0, tk.END)
        output = ""
        for i, disk in enumerate(self.simulator.disks):
            output += f"Disk {i}: {disk}\n"
        self.output_text.insert(tk.END, output)
        self.draw_disk_layout()

    def save_raid(self):
        # Save RAID state
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file:
            self.simulator.save_state(file)
            messagebox.showinfo("Saved", "RAID state saved successfully!")

    def load_raid(self):
        # Load RAID state
        file = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file:
            self.simulator.load_state(file)
            self.update_display()
            messagebox.showinfo("Loaded", "RAID state loaded successfully!")

if __name__ == "__main__":
    root = tk.Tk()
    gui = RAIDGUI(root)
    root.mainloop()
