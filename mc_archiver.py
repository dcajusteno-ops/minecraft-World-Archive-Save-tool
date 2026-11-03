import os
import shutil
import unicodedata
import zipfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


def display_width(text):
    """按显示宽度计算字符串长度：中文/全角字符算 2，其余算 1。"""
    return sum(
        2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        for ch in str(text)
    )


def fit_combobox_popdown(combobox, values, min_width=20):
    """把下拉列表的宽度撑到能完整显示最长选项，避免长版本名被截断。

    ttk.Combobox 的下拉列表默认与输入框同宽，版本名一长就看不全。
    这里直接调整下拉列表内部 Listbox 的字符宽度。
    """
    values = [v for v in values if str(v)]
    if not values:
        return
    width = max(max(display_width(v) for v in values) + 2, min_width)
    try:
        popdown = combobox.tk.call("ttk::combobox::PopdownWindow", combobox)
        combobox.tk.call(f"{popdown}.f.l", "configure", "-width", str(width))
    except tk.TclError:
        # 内部窗口结构因 ttk 主题而异，取不到就静默跳过，不影响主流程
        pass


class MinecraftArchiverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft 存档打包与导入工具")
        self.root.geometry("760x560")
        self.root.minsize(640, 460)
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.export_frame = ttk.Frame(self.notebook)
        self.import_frame = ttk.Frame(self.notebook)
        self.migrate_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.export_frame, text="打包导出")
        self.notebook.add(self.import_frame, text="一键导入")
        self.notebook.add(self.migrate_frame, text="版本数据迁移")
        
        self.setup_export_tab()
        self.setup_import_tab()
        self.setup_migrate_tab()
        
    def setup_export_tab(self):
        # Path selection
        frame1 = ttk.Frame(self.export_frame)
        frame1.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(frame1, text=".minecraft 路径:").pack(side=tk.LEFT)
        self.export_mc_path_var = tk.StringVar()
        ttk.Entry(frame1, textvariable=self.export_mc_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(frame1, text="浏览...", command=self.browse_export_mc_path).pack(side=tk.LEFT)
        
        # Scan button
        ttk.Button(self.export_frame, text="扫描存档", command=self.scan_saves).pack(pady=5)
        
        # Listbox for saves
        frame2 = ttk.Frame(self.export_frame)
        frame2.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.saves_listbox = tk.Listbox(frame2, selectmode=tk.SINGLE)
        v_scrollbar = ttk.Scrollbar(frame2, orient=tk.VERTICAL, command=self.saves_listbox.yview)
        h_scrollbar = ttk.Scrollbar(frame2, orient=tk.HORIZONTAL, command=self.saves_listbox.xview)
        self.saves_listbox.config(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # 用 grid 组合两个滚动条，长版本名/存档名可以横向滚动查看
        frame2.rowconfigure(0, weight=1)
        frame2.columnconfigure(0, weight=1)
        self.saves_listbox.grid(row=0, column=0, sticky=tk.NSEW)
        v_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        h_scrollbar.grid(row=1, column=0, sticky=tk.EW)
        
        # Export button
        ttk.Button(self.export_frame, text="打包选中的存档", command=self.export_save).pack(pady=10)
        
        self.found_saves = [] # Store full paths of saves
        
    def browse_export_mc_path(self):
        path = filedialog.askdirectory(title="选择 .minecraft 文件夹")
        if path:
            self.export_mc_path_var.set(path)
            
    def scan_saves(self):
        mc_path = self.export_mc_path_var.get()
        if not mc_path or not os.path.exists(mc_path):
            messagebox.showerror("错误", "请先选择有效的 .minecraft 文件夹路径。")
            return
            
        self.saves_listbox.delete(0, tk.END)
        self.found_saves.clear()
        
        # Global saves
        global_saves_dir = os.path.join(mc_path, "saves")
        if os.path.exists(global_saves_dir):
            for item in os.listdir(global_saves_dir):
                save_path = os.path.join(global_saves_dir, item)
                if os.path.isdir(save_path) and os.path.exists(os.path.join(save_path, "level.dat")):
                    self.found_saves.append(save_path)
                    self.saves_listbox.insert(tk.END, f"[全局] {item}")
                    
        # Version-isolated saves
        versions_dir = os.path.join(mc_path, "versions")
        if os.path.exists(versions_dir):
            for version in os.listdir(versions_dir):
                version_saves_dir = os.path.join(versions_dir, version, "saves")
                if os.path.exists(version_saves_dir):
                    for item in os.listdir(version_saves_dir):
                        save_path = os.path.join(version_saves_dir, item)
                        if os.path.isdir(save_path) and os.path.exists(os.path.join(save_path, "level.dat")):
                            self.found_saves.append(save_path)
                            self.saves_listbox.insert(tk.END, f"[{version}] {item}")
                            
        if not self.found_saves:
            messagebox.showinfo("提示", "未找到任何存档。")
            
    def export_save(self):
        selection = self.saves_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个存档。")
            return
            
        index = selection[0]
        save_path = self.found_saves[index]
        save_name_with_location = self.saves_listbox.get(index)
        
        # Format the default filename safely (replace spaces with underscores, avoid illegal chars if any)
        default_filename = f"{save_name_with_location}.zip".replace(" ", "_").replace("/", "_").replace("\\", "_")
        
        save_file = filedialog.asksaveasfilename(
            defaultextension=".zip",
            initialfile=default_filename,
            title="保存存档 ZIP 文件",
            filetypes=[("ZIP 压缩文件", "*.zip")]
        )
        
        if not save_file:
            return
            
        try:
            with zipfile.ZipFile(save_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(save_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Create relative path to the save folder name
                        rel_path = os.path.relpath(file_path, os.path.dirname(save_path))
                        zipf.write(file_path, rel_path)
            messagebox.showinfo("成功", f"存档已成功打包至:\n{save_file}")
        except Exception as e:
            messagebox.showerror("打包失败", str(e))
            
    def setup_import_tab(self):
        # Target MC Path
        frame1 = ttk.Frame(self.import_frame)
        frame1.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(frame1, text="目标 .minecraft 路径:").pack(side=tk.LEFT)
        self.import_mc_path_var = tk.StringVar()
        ttk.Entry(frame1, textvariable=self.import_mc_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(frame1, text="浏览...", command=self.browse_import_mc_path).pack(side=tk.LEFT)
        
        # Select Archive
        frame2 = ttk.Frame(self.import_frame)
        frame2.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(frame2, text="存档 ZIP 文件:").pack(side=tk.LEFT)
        self.import_zip_path_var = tk.StringVar()
        ttk.Entry(frame2, textvariable=self.import_zip_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(frame2, text="选择...", command=self.browse_import_zip).pack(side=tk.LEFT)
        
        # Scan Targets Button
        ttk.Button(self.import_frame, text="扫描可导入位置", command=self.scan_import_targets).pack(pady=5)
        
        # Target Selection Combobox
        frame3 = ttk.Frame(self.import_frame)
        frame3.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(frame3, text="导入到:").pack(side=tk.LEFT)
        self.target_combobox = ttk.Combobox(frame3, state="readonly")
        self.target_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.import_targets = {} # Label -> Path
        
        # Import button
        ttk.Button(self.import_frame, text="一键导入", command=self.import_save).pack(pady=20)
        
    def browse_import_mc_path(self):
        path = filedialog.askdirectory(title="选择目标 .minecraft 文件夹")
        if path:
            self.import_mc_path_var.set(path)
            
    def browse_import_zip(self):
        path = filedialog.askopenfilename(
            title="选择要导入的存档 ZIP 文件",
            filetypes=[("ZIP 压缩文件", "*.zip")]
        )
        if path:
            self.import_zip_path_var.set(path)
            
    def scan_import_targets(self):
        mc_path = self.import_mc_path_var.get()
        if not mc_path or not os.path.exists(mc_path):
            messagebox.showerror("错误", "请先选择有效的目标 .minecraft 文件夹路径。")
            return
            
        self.import_targets.clear()
        
        # Global
        global_saves = os.path.join(mc_path, "saves")
        self.import_targets["[全局存档] saves"] = global_saves
        
        # Versions
        versions_dir = os.path.join(mc_path, "versions")
        if os.path.exists(versions_dir):
            for version in os.listdir(versions_dir):
                version_path = os.path.join(versions_dir, version)
                if os.path.isdir(version_path):
                    self.import_targets[f"[{version}]"] = os.path.join(version_path, "saves")
                    
        self.target_combobox['values'] = list(self.import_targets.keys())
        # 撑宽下拉列表，长版本名在下拉菜单里也能完整显示
        fit_combobox_popdown(self.target_combobox, list(self.import_targets.keys()))
        if self.target_combobox['values']:
            self.target_combobox.current(0)
            messagebox.showinfo("提示", "已找到可导入的目标位置，请在下拉列表中选择。")
        else:
            messagebox.showwarning("警告", "未找到可导入的目标位置。")
            
    def import_save(self):
        mc_path = self.import_mc_path_var.get()
        zip_path = self.import_zip_path_var.get()
        target_label = self.target_combobox.get()
        
        if not mc_path or not os.path.exists(mc_path):
            messagebox.showerror("错误", "请选择有效的目标 .minecraft 路径。")
            return
        if not zip_path or not os.path.exists(zip_path):
            messagebox.showerror("错误", "请选择要导入的 ZIP 文件。")
            return
        if not target_label:
            messagebox.showerror("错误", "请选择要导入到的目标位置。")
            return
            
        target_saves_dir = self.import_targets[target_label]
        
        # Ensure target saves directory exists
        if not os.path.exists(target_saves_dir):
            try:
                os.makedirs(target_saves_dir)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建目标存档文件夹: {e}")
                return
                
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(target_saves_dir)
            messagebox.showinfo("成功", f"存档已成功导入至:\n{target_saves_dir}")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))

    def setup_migrate_tab(self):
        # MC Path Selection
        frame1 = ttk.Frame(self.migrate_frame)
        frame1.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(frame1, text=".minecraft 路径:").pack(side=tk.LEFT)
        self.migrate_mc_path_var = tk.StringVar()
        ttk.Entry(frame1, textvariable=self.migrate_mc_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(frame1, text="浏览...", command=self.browse_migrate_mc_path).pack(side=tk.LEFT)
        
        ttk.Button(self.migrate_frame, text="扫描版本", command=self.scan_migrate_versions).pack(pady=5)
        
        # Source and Target Version Selection
        frame2 = ttk.Frame(self.migrate_frame)
        frame2.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame2, text="源版本 (旧):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.source_version_cb = ttk.Combobox(frame2, state="readonly")
        self.source_version_cb.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)

        ttk.Label(frame2, text="目标版本 (新):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.target_version_cb = ttk.Combobox(frame2, state="readonly")
        self.target_version_cb.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)

        frame2.columnconfigure(1, weight=1)

        # 完整版本名回显：版本名过长时，下拉框会被截断，这里换行完整展示
        self.source_version_full_var = self.create_full_name_row(
            self.migrate_frame, "源版本完整名称:", "（尚未选择）", "source"
        )
        self.target_version_full_var = self.create_full_name_row(
            self.migrate_frame, "目标版本完整名称:", "（尚未选择）", "target"
        )

        self.source_version_cb.bind("<<ComboboxSelected>>", self.update_version_labels)
        self.target_version_cb.bind("<<ComboboxSelected>>", self.update_version_labels)
        
        # Checkboxes for items to migrate
        frame3 = ttk.LabelFrame(self.migrate_frame, text="选择要迁移的内容 (将覆盖目标版本同名文件)")
        frame3.pack(fill=tk.X, padx=10, pady=10)
        
        self.migrate_vars = {
            'mods': tk.BooleanVar(value=True),
            'config': tk.BooleanVar(value=True),
            'saves': tk.BooleanVar(value=True),
            'resourcepacks': tk.BooleanVar(value=True),
            'shaderpacks': tk.BooleanVar(value=True)
        }
        
        for i, (key, var) in enumerate(self.migrate_vars.items()):
            ttk.Checkbutton(frame3, text=key, variable=var).grid(row=0, column=i, padx=10, pady=5)
            
        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.migrate_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)
        
        # Migrate Button
        ttk.Button(self.migrate_frame, text="开始迁移", command=self.migrate_version_data).pack(pady=10)
        
        self.migrate_versions = []

    def browse_migrate_mc_path(self):
        path = filedialog.askdirectory(title="选择 .minecraft 文件夹")
        if path:
            self.migrate_mc_path_var.set(path)

    def create_full_name_row(self, parent, title, placeholder, key):
        """创建一行「完整名称」回显标签，宽度不足时自动换行，保证长版本名完整可见。"""
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, padx=10, pady=(0, 4))

        ttk.Label(row, text=title, width=16, anchor=tk.W).pack(side=tk.LEFT, anchor=tk.N)

        var = tk.StringVar(value=placeholder)
        # 给一个初始换行宽度，保证控件映射前也不会被截断
        label = ttk.Label(row, textvariable=var, anchor=tk.W, justify=tk.LEFT, wraplength=460)
        label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 跟随窗口宽度动态调整换行点
        def on_configure(event, lbl=label):
            lbl.configure(wraplength=max(event.width - 150, 80))

        row.bind("<Configure>", on_configure)

        if not hasattr(self, "_full_name_labels"):
            self._full_name_labels = {}
        self._full_name_labels[key] = label
        return var

    def update_version_labels(self, event=None):
        """把当前选中的版本名同步到「完整名称」回显行。"""
        for key, combobox in (("source", self.source_version_cb), ("target", self.target_version_cb)):
            var = getattr(self, f"{key}_version_full_var", None)
            if var is None:
                continue
            name = combobox.get().strip()
            var.set(name if name else "（尚未选择）")

    def scan_migrate_versions(self):
        mc_path = self.migrate_mc_path_var.get()
        if not mc_path or not os.path.exists(mc_path):
            messagebox.showerror("错误", "请先选择有效的 .minecraft 文件夹路径。")
            return
            
        versions_dir = os.path.join(mc_path, "versions")
        self.migrate_versions = []
        if os.path.exists(versions_dir):
            for version in os.listdir(versions_dir):
                if os.path.isdir(os.path.join(versions_dir, version)):
                    self.migrate_versions.append(version)
                    
        if self.migrate_versions:
            self.source_version_cb['values'] = self.migrate_versions
            self.target_version_cb['values'] = self.migrate_versions
            self.source_version_cb.current(0)
            self.target_version_cb.current(0)
            # 撑宽下拉列表，长版本名在下拉菜单里也能完整显示
            fit_combobox_popdown(self.source_version_cb, self.migrate_versions)
            fit_combobox_popdown(self.target_version_cb, self.migrate_versions)
            self.update_version_labels()
            messagebox.showinfo("提示", f"找到 {len(self.migrate_versions)} 个版本，请在下拉列表中选择。")
        else:
            self.source_version_cb['values'] = []
            self.target_version_cb['values'] = []
            self.source_version_cb.set('')
            self.target_version_cb.set('')
            self.update_version_labels()
            messagebox.showwarning("警告", "未在 versions 文件夹下找到任何版本。")

    def migrate_version_data(self):
        mc_path = self.migrate_mc_path_var.get()
        source_ver = self.source_version_cb.get()
        target_ver = self.target_version_cb.get()
        
        if not mc_path or not source_ver or not target_ver:
            messagebox.showerror("错误", "请选择 .minecraft 路径以及源版本和目标版本。")
            return
            
        if source_ver == target_ver:
            messagebox.showwarning("警告", "源版本和目标版本不能相同。")
            return
            
        source_dir = os.path.join(mc_path, "versions", source_ver)
        target_dir = os.path.join(mc_path, "versions", target_ver)
        
        if not os.path.exists(source_dir) or not os.path.exists(target_dir):
            messagebox.showerror("错误", "源版本或目标版本文件夹不存在。")
            return
            
        # Calculate total size
        total_size = 0
        for folder_name, var in self.migrate_vars.items():
            if var.get():
                src_folder = os.path.join(source_dir, folder_name)
                if os.path.exists(src_folder):
                    for root_dir, _, files in os.walk(src_folder):
                        for file in files:
                            try:
                                total_size += os.path.getsize(os.path.join(root_dir, file))
                            except Exception:
                                pass
                                
        self.progress_var.set(0)
        self.progress_bar['maximum'] = total_size if total_size > 0 else 1
        copied_size = 0
        
        def copy_with_progress(src, dst, *, follow_symlinks=True):
            nonlocal copied_size
            shutil.copy2(src, dst)
            try:
                copied_size += os.path.getsize(src)
                self.progress_var.set(copied_size)
                self.root.update_idletasks()
            except Exception:
                pass
            return dst

        success_items = []
        failed_items = []
        
        for folder_name, var in self.migrate_vars.items():
            if var.get():
                src_folder = os.path.join(source_dir, folder_name)
                dst_folder = os.path.join(target_dir, folder_name)
                
                if os.path.exists(src_folder):
                    try:
                        shutil.copytree(src_folder, dst_folder, dirs_exist_ok=True, copy_function=copy_with_progress)
                        success_items.append(folder_name)
                    except Exception as e:
                        failed_items.append(f"{folder_name} ({e})")
                else:
                    # Folder does not exist in source, skip
                    pass
                    
        self.progress_var.set(self.progress_bar['maximum'])
        self.root.update_idletasks()
        
        if failed_items:
            messagebox.showwarning("部分完成", f"以下文件夹迁移成功: {', '.join(success_items)}\n\n以下文件夹迁移失败: {', '.join(failed_items)}")
        else:
            if success_items:
                messagebox.showinfo("成功", f"迁移成功！包含的内容: {', '.join(success_items)}")
            else:
                messagebox.showinfo("提示", "未找到需要迁移的文件，或者您没有勾选任何选项。")
                
        self.progress_var.set(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = MinecraftArchiverApp(root)
    root.mainloop()
