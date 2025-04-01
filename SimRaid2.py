
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import json
import time
from itertools import combinations

MAX_BLOCKS_PER_DISK = 100

class RAIDSimulator:
    def __init__(self, num_disks=4, raid_level='5'):
        if raid_level not in {'0', '1', '5', '6', '10'}:
            raise ValueError("Unsupported RAID level. Choose 0, 1, 5, 6, or 10.")
        if raid_level == '0' and num_disks < 2:
            raise ValueError("RAID 0 requires at least 2 disks.")
        if raid_level == '1' and num_disks < 2:
            raise ValueError("RAID 1 requires at least 2 disks.")
        if raid_level == '5' and num_disks < 3:
            raise ValueError("RAID 5 requires at least 3 disks.")
        if raid_level == '6' and num_disks < 4:
            raise ValueError("RAID 6 requires at least 4 disks.")
        if raid_level == '10' and (num_disks < 4 or num_disks % 2 != 0 or num_disks > 32):
            raise ValueError("RAID 10 requires at least 4 disks and must be even.")

        self.num_disks = num_disks
        self.raid_level = raid_level
        self.disks = [[] for _ in range(num_disks)]

    def write_data(self, data_blocks):
        if len(self.disks[0]) + len(data_blocks) > MAX_BLOCKS_PER_DISK:
            raise ValueError(f"Exceeded maximum block size per disk ({MAX_BLOCKS_PER_DISK}). Reduce input size.")

        if self.raid_level == '5':
            stripe_size = self.num_disks - 1
        elif self.raid_level == '6':
            stripe_size = self.num_disks - 2
        else:
            stripe_size = self.num_disks

        start_time = time.time()

        if self.raid_level in {'5', '6'}:
            for stripe_start in range(0, len(data_blocks), stripe_size):
                stripe = data_blocks[stripe_start:stripe_start + stripe_size]
                if len(stripe) < stripe_size:
                    stripe += ['_'] * (stripe_size - len(stripe))

                stripe_num = len(self.disks[0])
                parity_pos = stripe_num % self.num_disks
                if self.raid_level == '6':
                    q_parity_pos = (parity_pos + 1) % self.num_disks

                p_parity = self.calculate_p_parity(stripe)
                if self.raid_level == '6':
                    q_parity = self.calculate_q_parity(stripe)

                data_index = 0
                for disk_idx in range(self.num_disks):
                    if disk_idx == parity_pos:
                        self.disks[disk_idx].append(f"P({p_parity})")
                    elif self.raid_level == '6' and disk_idx == q_parity_pos:
                        self.disks[disk_idx].append(f"Q({q_parity})")
                    else:
                        self.disks[disk_idx].append(stripe[data_index])
                        data_index += 1
        elif self.raid_level == '0':
            for i, block in enumerate(data_blocks):
                self.disks[i % self.num_disks].append(block)
        elif self.raid_level == '1':
            for block in data_blocks:
                for disk in self.disks:
                    disk.append(block)
        elif self.raid_level == '10':
            half = self.num_disks // 2
            for i, block in enumerate(data_blocks):
                stripe_idx = i % half
                self.disks[stripe_idx].append(block)
                self.disks[stripe_idx + half].append(block)

        elapsed = time.time() - start_time
        return elapsed

    def calculate_p_parity(self, blocks):
        parity = 0
        for block in blocks:
            if block not in {'_', 'X'}:
                parity ^= ord(block)
        return hex(parity)[2:].upper().zfill(2)

    def calculate_q_parity(self, blocks):
        q = 0
        for i, block in enumerate(blocks):
            if block not in {'_', 'X'}:
                q ^= self.gf_mult(ord(block), (i + 1))
        return hex(q)[2:].upper().zfill(2)

    def gf_mult(self, a, b):
        result = 0
        for _ in range(8):
            if b & 1:
                result ^= a
            hi_bit_set = a & 0x80
            a <<= 1
            if hi_bit_set:
                a ^= 0x1d
            b >>= 1
        return result

    def gf_inverse(self, a):
        """Compute multiplicative inverse in GF(2^8) using extended Euclidean algorithm"""
        if a == 0:
            return 0
        for b in range(1, 256):
            if self.gf_mult(a, b) == 1:
                return b
        return 0  # Should never happen for non-zero a

    def simulate_failure_and_recovery(self, failed_indices):
        if not all(0 <= idx < self.num_disks for idx in failed_indices):
            raise ValueError("Invalid disk index.")

        if self.raid_level == '0':
            raise ValueError("RAID 0 does not support recovery.")
        if self.raid_level == '5' and len(failed_indices) > 1:
            raise ValueError("RAID 5 can only tolerate 1 disk failure.")
        if self.raid_level == '6' and len(failed_indices) > 2:
            raise ValueError("RAID 6 can only tolerate up to 2 disk failures.")
        if self.raid_level == '10':
            half = self.num_disks // 2
            for idx in failed_indices:
                mirror_idx = idx - half if idx >= half else idx + half
                if mirror_idx in failed_indices:
                    raise ValueError("RAID 10 cannot recover if both disks in mirrored pair fail.")

        for idx in failed_indices:
            self.disks[idx] = ['X'] * len(self.disks[0])

        recovered_data = []

        if self.raid_level == '1':
            for idx in failed_indices:
                mirror_idx = (idx + 1) % self.num_disks  # Simple mirroring
                self.disks[idx] = self.disks[mirror_idx].copy()
                recovered_data.append(self.disks[idx])
        
        elif self.raid_level == '5':
            failed_idx = failed_indices[0]
            recovered_blocks = []

            for block_idx in range(len(self.disks[0])):
                parity_pos = block_idx % self.num_disks

                if failed_idx == parity_pos:
                    # Reconstruct parity
                    parity = 0
                    for disk_idx in range(self.num_disks):
                        if disk_idx != failed_idx:
                            block = self.disks[disk_idx][block_idx]
                            if isinstance(block, str) and block.isprintable() and not block.startswith(('P(', 'Q(')) and block not in {'X', '_'}:
                                parity ^= ord(block)
                    recovered_blocks.append(f"P({hex(parity)[2:].upper().zfill(2)})")
                else:
                    # Reconstruct data
                    recovery_block = 0
                    for disk_idx in range(self.num_disks):
                        if disk_idx != failed_idx:
                            block = self.disks[disk_idx][block_idx]
                            if block.startswith('P(') and disk_idx == parity_pos:
                                recovery_block ^= int(block[2:-1], 16)
                            elif block not in {'X', '_'}:
                                recovery_block ^= ord(block)
                    recovered_blocks.append(f"{recovery_block:02X}")

            self.disks[failed_idx] = recovered_blocks
            recovered_data.append(recovered_blocks)

        elif self.raid_level == '6':
            if len(failed_indices) == 1:
                failed_idx = failed_indices[0]
                recovered_blocks = []

                for block_idx in range(len(self.disks[0])):
                    parity_pos = block_idx % self.num_disks
                    q_pos = (parity_pos + 1) % self.num_disks

                    if failed_idx == parity_pos:
                        # Reconstruct P parity
                        p_parity = 0
                        for disk_idx in range(self.num_disks):
                            if disk_idx != failed_idx:
                                block = self.disks[disk_idx][block_idx]
                                if block.startswith('Q('):
                                    continue
                                if block not in {'X', '_'} and not block.startswith('P('):
                                    p_parity ^= ord(block)
                        recovered_blocks.append(f"P({hex(p_parity)[2:].upper().zfill(2)})")
                    elif failed_idx == q_pos:
                        # Reconstruct Q parity
                        q_parity = 0
                        for disk_idx in range(self.num_disks):
                            if disk_idx != failed_idx:
                                block = self.disks[disk_idx][block_idx]
                                if block.startswith('P('):
                                    continue
                                if block not in {'X', '_'} and not block.startswith('Q('):
                                    q_parity ^= self.gf_mult(ord(block), (disk_idx + 1))
                        recovered_blocks.append(f"Q({hex(q_parity)[2:].upper().zfill(2)})")
                    else:
                        # Reconstruct data block
                        # Get available data and parity
                        available_data = {}
                        p_val = None
                        q_val = None
                        
                        for disk_idx in range(self.num_disks):
                            if disk_idx != failed_idx:
                                block = self.disks[disk_idx][block_idx]
                                if block.startswith('P('):
                                    p_val = int(block[2:-1], 16)
                                elif block.startswith('Q('):
                                    q_val = int(block[2:-1], 16)
                                elif block not in {'X', '_'}:
                                    available_data[disk_idx] = ord(block)
                        
                        # Calculate sum of known data
                        sum_known = 0
                        q_sum_known = 0
                        for disk_idx, val in available_data.items():
                            sum_known ^= val
                            q_sum_known ^= self.gf_mult(val, disk_idx + 1)
                        
                        # Reconstruct missing data
                        missing_data = p_val ^ sum_known
                        
                        # Verify with Q parity
                        calculated_q = q_sum_known ^ self.gf_mult(missing_data, failed_idx + 1)
                        if calculated_q != q_val:
                            # If verification fails, use Q parity to reconstruct
                            missing_data = self.gf_mult(
                                (q_val ^ q_sum_known),
                                self.gf_inverse(failed_idx + 1)
                            )
                        
                        recovered_blocks.append(chr(missing_data))

                self.disks[failed_idx] = recovered_blocks
                recovered_data.append(recovered_blocks)

            else:  # Dual disk failure
                failed1, failed2 = sorted(failed_indices)
                recovered1 = []
                recovered2 = []

                for block_idx in range(len(self.disks[0])):
                    parity_pos = block_idx % self.num_disks
                    q_pos = (parity_pos + 1) % self.num_disks

                    # Collect available data and parity
                    available_data = {}
                    p_val = None
                    q_val = None
                    
                    for i in range(self.num_disks):
                        if i not in failed_indices:
                            block = self.disks[i][block_idx]
                            if block.startswith('P('):
                                p_val = int(block[2:-1], 16)
                            elif block.startswith('Q('):
                                q_val = int(block[2:-1], 16)
                            elif block not in {'X', '_'}:
                                available_data[i] = ord(block)

                    # Case 1: Both failed disks are parity disks
                    if failed1 == parity_pos and failed2 == q_pos:
                        # Reconstruct both parity blocks from data
                        p_calc = 0
                        q_calc = 0
                        for i, val in available_data.items():
                            p_calc ^= val
                            q_calc ^= self.gf_mult(val, i + 1)
                        recovered1.append(f"P({hex(p_calc)[2:].upper().zfill(2)})")
                        recovered2.append(f"Q({hex(q_calc)[2:].upper().zfill(2)})")
                    
                    # Case 2: One parity and one data disk failed
                    elif failed1 == parity_pos or failed2 == parity_pos:
                        # Determine which is the data disk
                        failed_data_pos = failed2 if failed1 == parity_pos else failed1
                        
                        # Calculate known sums
                        sum_known = 0
                        q_sum_known = 0
                        for i, val in available_data.items():
                            sum_known ^= val
                            q_sum_known ^= self.gf_mult(val, i + 1)
                        
                        # Reconstruct the data block
                        coeff = failed_data_pos + 1
                        missing_data = self.gf_mult(
                            (p_val ^ sum_known) ^ self.gf_mult((q_val ^ q_sum_known), self.gf_inverse(coeff)),
                            self.gf_inverse(1 ^ coeff)
                        )
                        
                        # Reconstruct the parity block
                        if failed1 == parity_pos:
                            recovered1.append(f"P({hex(p_val)[2:].upper().zfill(2)})")
                            recovered2.append(chr(missing_data))
                        else:
                            recovered1.append(chr(missing_data))
                            recovered2.append(f"P({hex(p_val)[2:].upper().zfill(2)})")
                    
                    # Case 3: Both failed disks are data disks
                    else:
                        # Calculate known sums
                        sum_known = 0
                        q_sum_known = 0
                        for i, val in available_data.items():
                            sum_known ^= val
                            q_sum_known ^= self.gf_mult(val, i + 1)
                        
                        # Coefficients for the failed disks
                        a = failed1 + 1
                        b = failed2 + 1
                        
                        # Calculate determinants
                        delta = 1 ^ self.gf_mult(a, self.gf_inverse(b))
                        delta_x = (p_val ^ sum_known) ^ self.gf_mult((q_val ^ q_sum_known), self.gf_inverse(b))
                        delta_y = self.gf_mult((p_val ^ sum_known), self.gf_inverse(a)) ^ (q_val ^ q_sum_known)
                        
                        # Solve for the missing data blocks
                        d1 = self.gf_mult(delta_x, self.gf_inverse(delta))
                        d2 = self.gf_mult(delta_y, self.gf_inverse(delta))
                        
                        recovered1.append(f"{d1:02X}")
                        recovered2.append(f"{d2:02X}")

                self.disks[failed1] = recovered1
                self.disks[failed2] = recovered2
                recovered_data.append(recovered1)
                recovered_data.append(recovered2)

        elif self.raid_level == '10':
            half = self.num_disks // 2
            for idx in failed_indices:
                mirror_idx = idx - half if idx >= half else idx + half
                self.disks[idx] = self.disks[mirror_idx].copy()
                recovered_data.append(self.disks[idx])

        return recovered_data

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

        tk.Label(self.input_frame, text="RAID Level (0, 1, 5, 6, 10):", bg="#f0f0f0").pack()
        self.level_var = tk.StringVar(value='5')
        self.level_menu = ttk.Combobox(self.input_frame, textvariable=self.level_var, values=['0', '1', '5', '6', '10'])
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
                color = "#AED6F1" if "P" in block else ("#F1948A" if block == 'X' else ("#F9E79F" if "Q" in block else "#ABEBC6"))
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