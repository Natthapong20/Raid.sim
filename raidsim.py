# raid_simulator.py with GUI using Tkinter and basic animation
import tkinter as tk
from tkinter import messagebox
import time

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
        if self.raid_level == '0':
            for i, block in enumerate(data_blocks):
                self.disks[i % self.num_disks].append(block)

        elif self.raid_level == '1':
            for block in data_blocks:
                for disk in self.disks:
                    disk.append(block)

        elif self.raid_level in {'5', '6'}:
            stripe_size = self.num_disks - (2 if self.raid_level == '6' else 1)
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
                        self.disks[j].append(parity1)
                    elif self.raid_level == '6' and j == parity_index2:
                        self.disks[j].append(parity2)
                    else:
                        self.disks[j].append(stripe[disk_idx])
                        disk_idx += 1

    def calculate_parity(self, blocks):
        parity = ord(blocks[0])
        for block in blocks[1:]:
            parity ^= ord(block)
        return chr(parity)

    def simulate_failure_and_recovery(self, failed_index):
        if failed_index < 0 or failed_index >= self.num_disks:
            raise ValueError("Invalid disk index")
        failed_data = self.disks[failed_index]
        self.disks[failed_index] = ['X'] * len(failed_data)
        if self.raid_level in {'5', '6'}:
            recovered = []
            for block_index in range(len(failed_data)):
                recovered_block = 0
                for disk_index in range(self.num_disks):
                    if disk_index == failed_index:
                        continue
                    recovered_block ^= ord(self.disks[disk_index][block_index])
                recovered.append(chr(recovered_block))
            self.disks[failed_index] = recovered

class RAIDGUI:
    def __init__(self, master):
        self.master = master
        master.title("RAID Simulator")

        self.level_label = tk.Label(master, text="RAID Level (0, 1, 5, 6):")
        self.level_label.pack()
        self.level_entry = tk.Entry(master)
        self.level_entry.insert(0, '5')
        self.level_entry.pack()

        self.disk_label = tk.Label(master, text="Number of Disks:")
        self.disk_label.pack()
        self.disk_entry = tk.Entry(master)
        self.disk_entry.insert(0, '4')
        self.disk_entry.pack()

        self.input_label = tk.Label(master, text="Input Data:")
        self.input_label.pack()
        self.data_entry = tk.Entry(master)
        self.data_entry.pack()

        self.write_button = tk.Button(master, text="Write Data", command=self.write_data)
        self.write_button.pack()

        self.fail_label = tk.Label(master, text="Simulate Disk Failure (0-n):")
        self.fail_label.pack()
        self.fail_entry = tk.Entry(master)
        self.fail_entry.pack()

        self.recover_button = tk.Button(master, text="Recover Disk", command=self.recover_disk)
        self.recover_button.pack()

        self.output_text = tk.Text(master, height=15, width=70)
        self.output_text.pack()

    def animate_text(self, text):
        self.output_text.delete(1.0, tk.END)
        for line in text.splitlines():
            self.output_text.insert(tk.END, line + '\n')
            self.output_text.update()
            time.sleep(0.2)  # animation delay

    def write_data(self):
        try:
            level = self.level_entry.get()
            num_disks = int(self.disk_entry.get())
            self.simulator = RAIDSimulator(num_disks=num_disks, raid_level=level)
            data = self.data_entry.get()
            self.simulator.write_data(list(data))
            self.update_display(animated=True)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def recover_disk(self):
        try:
            index = int(self.fail_entry.get())
            self.simulator.simulate_failure_and_recovery(index)
            self.update_display(animated=True)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_display(self, animated=False):
        output = ""
        for i, disk in enumerate(self.simulator.disks):
            output += f"Disk {i}: {disk}\n"
        if animated:
            self.animate_text(output)
        else:
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, output)

if __name__ == "__main__":
    root = tk.Tk()
    gui = RAIDGUI(root)
    root.mainloop()
