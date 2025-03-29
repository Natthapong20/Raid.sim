import tkinter as tk
from tkinter import messagebox, ttk
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
        self.parity_positions = []  # เก็บตำแหน่งของ Parity สำหรับแสดงผล

    # ฟังก์ชันเขียนข้อมูลลงดิสก์ตามระดับ RAID
    def write_data(self, data_blocks):
        self.parity_positions = []  # รีเซ็ตตำแหน่ง parity ทุกครั้งที่เขียนข้อมูลใหม่

        if self.raid_level == '0':  # RAID 0 (Striping)
            for i, block in enumerate(data_blocks):
                self.disks[i % self.num_disks].append(block)

        elif self.raid_level == '1':  # RAID 1 (Mirroring)
            for block in data_blocks:
                for disk in self.disks:
                    disk.append(block)

        elif self.raid_level in {'5', '6'}:  # RAID 5/6
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
                        self.disks[j].append(f"P({parity1})")
                        self.parity_positions.append((j, len(self.disks[j]) - 1))
                    elif self.raid_level == '6' and j == parity_index2:
                        self.disks[j].append(f"P2({parity2})")
                        self.parity_positions.append((j, len(self.disks[j]) - 1))
                    else:
                        self.disks[j].append(stripe[disk_idx])
                        disk_idx += 1

    # คำนวณค่า parity (XOR)
    def calculate_parity(self, blocks):
        parity = ord(blocks[0])
        for block in blocks[1:]:
            parity ^= ord(block)
        return hex(parity)[2:].upper().zfill(2)

    # จำลองความเสียหายและการกู้คืนดิสก์
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
                    block_value = self.disks[disk_index][block_index]
                    if "P" in block_value or block_value in {'X', '_'}:
                        continue
                    recovered_block ^= ord(block_value)
                recovered.append(hex(recovered_block)[2:].upper().zfill(2))  # กู้คืนเป็น HEX
            self.disks[failed_index] = recovered
            return recovered
        return None


# ส่วน GUI
class RAIDGUI:
    def __init__(self, master):
        self.master = master
        master.title("RAID Simulator")

        # Frame หลัก
        self.main_frame = tk.Frame(master)
        self.main_frame.pack(padx=10, pady=10)

        # สร้าง frame สำหรับ Input
        self.input_frame = tk.Frame(self.main_frame)
        self.input_frame.pack(side=tk.LEFT, padx=10)

        self.level_label = tk.Label(self.input_frame, text="RAID Level (0, 1, 5, 6):")
        self.level_label.pack()
        self.level_var = tk.StringVar(value='5')
        self.level_menu = ttk.Combobox(self.input_frame, textvariable=self.level_var, values=['0', '1', '5', '6'])
        self.level_menu.pack()

        self.disk_label = tk.Label(self.input_frame, text="Number of Disks:")
        self.disk_label.pack()
        self.disk_entry = tk.Entry(self.input_frame)
        self.disk_entry.insert(0, '4')
        self.disk_entry.pack()

        self.input_label = tk.Label(self.input_frame, text="Input Data:")
        self.input_label.pack()
        self.data_entry = tk.Entry(self.input_frame)
        self.data_entry.pack()

        self.write_button = tk.Button(self.input_frame, text="Write Data", command=self.write_data)
        self.write_button.pack(pady=5)

        self.fail_label = tk.Label(self.input_frame, text="Simulate Disk Failure (0-n):")
        self.fail_label.pack()
        self.fail_entry = tk.Entry(self.input_frame)
        self.fail_entry.pack()

        self.recover_button = tk.Button(self.input_frame, text="Recover Disk", command=self.recover_disk)
        self.recover_button.pack(pady=5)

        # สร้าง frame สำหรับแสดงผล
        self.output_frame = tk.Frame(self.main_frame)
        self.output_frame.pack(side=tk.RIGHT, padx=10)

        self.output_canvas = tk.Canvas(self.output_frame, width=400, height=300, bg="white")
        self.output_canvas.pack()

        self.output_text = tk.Text(self.output_frame, height=10, width=50)
        self.output_text.pack(pady=5)

    # ฟังก์ชันแสดงผลกราฟิกตำแหน่งข้อมูลและ Parity
    def draw_disk_layout(self):
        self.output_canvas.delete("all")
        disk_width = 60
        disk_height = 40
        spacing = 20
        for i, disk in enumerate(self.simulator.disks):
            x = 20
            y = i * (disk_height + spacing) + 20
            self.output_canvas.create_rectangle(x, y, x + disk_width, y + disk_height, fill="lightgrey")
            self.output_canvas.create_text(x + 30, y + 20, text=f"Disk {i}", font=("Arial", 10, "bold"))

            for j, block in enumerate(disk):
                block_color = "lightblue" if "P" in block else "white"
                self.output_canvas.create_rectangle(x + 80 + j * 50, y, x + 120 + j * 50, y + disk_height, fill=block_color)
                self.output_canvas.create_text(x + 100 + j * 50, y + 20, text=block, font=("Arial", 9))

    # ฟังก์ชันเมื่อกดปุ่ม Write Data
    def write_data(self):
        try:
            level = self.level_var.get()
            num_disks = int(self.disk_entry.get())
            self.simulator = RAIDSimulator(num_disks=num_disks, raid_level=level)
            data = self.data_entry.get()
            self.simulator.write_data(list(data))
            self.update_display()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ฟังก์ชันเมื่อกดปุ่ม Recover Disk
    def recover_disk(self):
        try:
            index = int(self.fail_entry.get())
            recovered_data = self.simulator.simulate_failure_and_recovery(index)
            self.update_display()
            if recovered_data:
                summary = f"Disk {index} recovered successfully!\nRecovered Data: {recovered_data}\n"
                self.output_text.insert(tk.END, "\n" + summary)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ฟังก์ชันอัปเดตข้อมูลในหน้าต่างแสดงผล
    def update_display(self):
        self.output_text.delete(1.0, tk.END)
        output = ""
        for i, disk in enumerate(self.simulator.disks):
            disk_data = []
            for j, block in enumerate(disk):
                if (i, j) in self.simulator.parity_positions:
                    disk_data.append(f"{block} (P)")
                else:
                    disk_data.append(block)
            output += f"Disk {i}: {disk_data}\n"
        self.output_text.insert(tk.END, output)
        self.draw_disk_layout()


# เริ่มต้น GUI
if __name__ == "__main__":
    root = tk.Tk()
    gui = RAIDGUI(root)
    root.mainloop()
