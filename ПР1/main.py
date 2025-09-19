import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import datetime
import os
import json

DATE_FORMAT = "%d-%m-%Y"
DB_FILE = "tasks_buggy.db"

class TaskManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Менеджер задач (buggy)")
        self.tasks = []
        self._db_connect()
        self._build_ui()
        self.load_from_db()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _db_connect(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.cur = self.conn.cursor()
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due TEXT,
                priority TEXT,
                desc TEXT,
                done INTEGER DEFAULT 0,
                created TEXT
            )
        """)
        self.conn.commit()

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.grid(sticky="nsew")
        input_frame = ttk.LabelFrame(frm, text="Новая / Редактировать задача", padding=8)
        input_frame.grid(row=0, column=0, sticky="ew")
        ttk.Label(input_frame, text="Заголовок:").grid(row=0, column=0, sticky="w")
        self.title_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.title_var, width=40).grid(row=0, column=1, columnspan=3, sticky="w")
        ttk.Label(input_frame, text="Срок (YYYY-MM-DD):").grid(row=1, column=0, sticky="w", pady=(6,0))
        self.due_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.due_var, width=15).grid(row=1, column=1, sticky="w", pady=(6,0))
        ttk.Label(input_frame, text="Приоритет:").grid(row=1, column=2, sticky="w", padx=(10,0), pady=(6,0))
        self.prio_var = tk.StringVar(value="Средний")
        ttk.Combobox(input_frame, textvariable=self.prio_var, values=["Низкий","Средний","Высокий"], width=10, state="readonly").grid(row=1, column=3, sticky="w", pady=(6,0))
        ttk.Label(input_frame, text="Описание:").grid(row=2, column=0, sticky="nw", pady=(6,0))
        self.desc_text = tk.Text(input_frame, width=50, height=4)
        self.desc_text.grid(row=2, column=1, columnspan=3, pady=(6,0), sticky="w")
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=(8,0), sticky="w")
        ttk.Button(btn_frame, text="Добавить задачу", command=self.edit_task).grid(row=0, column=0)
        ttk.Button(btn_frame, text="Редактировать выбранную", command=self.add_task).grid(row=0, column=1, padx=6)
        ttk.Button(btn_frame, text="Удалить выбранную", command=self.delete_task).grid(row=0, column=2, padx=6)
        ttk.Button(btn_frame, text="Отметить/Снять выполнение", command=self.toggle_complete).grid(row=0, column=3, padx=6)
        view_frame = ttk.LabelFrame(frm, text="Список задач", padding=8)
        view_frame.grid(row=1, column=0, pady=(10,0), sticky="nsew")
        self.tree = ttk.Treeview(view_frame, columns=("title","due","prio","status"), show="headings", height=12)
        self.tree.heading("title", text="Заголовок")
        self.tree.heading("due", text="Срок")
        self.tree.heading("prio", text="Приоритет")
        self.tree.heading("status", text="Статус")
        self.tree.column("title", width=260)
        self.tree.column("due", width=90)
        self.tree.column("prio", width=80, anchor="center")
        self.tree.column("status", width=110, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(view_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")
        control_frame = ttk.Frame(frm)
        control_frame.grid(row=2, column=0, pady=(8,0), sticky="ew")
        ttk.Button(control_frame, text="Экспорт в JSON", command=self.export_json).grid(row=0, column=0)
        ttk.Button(control_frame, text="Импорт из JSON", command=self.import_json).grid(row=0, column=1, padx=6)
        ttk.Button(control_frame, text="Сброс фильтра", command=self.reset_filter).grid(row=0, column=2, padx=6)
        ttk.Button(control_frame, text="Сортировать по сроку", command=self.sort_tasks).grid(row=0, column=3, padx=6)
        ttk.Label(control_frame, text="Фильтр:").grid(row=1, column=0, sticky="w", pady=(8,0))
        self.filter_var = tk.StringVar(value="Все")
        ttk.Combobox(control_frame, textvariable=self.filter_var, values=["Все","Выполненные","Невыполненные","Высокий приоритет","Просроченные"], state="readonly", width=18).grid(row=1, column=1, pady=(8,0))
        ttk.Button(control_frame, text="Применить фильтр", command=self.apply_filter).grid(row=1, column=2, padx=6, pady=(8,0))
        ttk.Label(control_frame, text="Поиск:").grid(row=1, column=3, sticky="e", pady=(8,0))
        self.search_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.search_var, width=24).grid(row=1, column=4, sticky="w", pady=(8,0))
        ttk.Button(control_frame, text="Найти", command=self.search_tasks).grid(row=1, column=5, padx=6, pady=(8,0))
        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(frm, textvariable=self.status_var).grid(row=3, column=0, sticky="w", pady=(6,0))
        self.root.columnconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)
        view_frame.columnconfigure(0, weight=1)
        view_frame.rowconfigure(0, weight=1)

    def add_task(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showinfo("Ошибка","Введите заголовок задачи")
            return
        due = self.due_var.get().strip()
        if due:
            try:
                datetime.datetime.strptime(due, DATE_FORMAT)
            except Exception:
                messagebox.showinfo("Ошибка","Неверный формат даты")
                return
        prio = self.prio_var.get()
        desc = self.desc_text.get("1.0","end").strip()
        created = datetime.datetime.now().isoformat()
        self.cur.execute("INSERT INTO tasks (title,due,priority,desc,done,created) VALUES (?,?,?,?,?,?)", (title or "", due or "", prio or "", desc or "", 0, created))
        self.conn.commit()
        rowid = self.cur.lastrowid
        task = {"id": rowid, "title": title, "due": due, "priority": prio, "desc": desc, "done": False, "created": created}
        self.tasks.append(task)
        self.update_view()
        self.clear_inputs()
        self.status_var.set("Задача добавлена (автосохранено)")

    def edit_task(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Инфо","Выберите задачу для редактирования")
            return
        item_id = int(sel[0])
        task = next((t for t in self.tasks if t["id"]==item_id), None)
        if not task:
            messagebox.showinfo("Ошибка","Задача не найдена")
            return
        self.title_var.set(task["title"])
        self.due_var.set(task["due"])
        self.prio_var.set(task["priority"])
        self.desc_text.delete("1.0","end")
        self.desc_text.insert("1.0", task["desc"])
        def save_edit():
            title = self.title_var.get().strip()
            if not title:
                messagebox.showinfo("Ошибка","Введите заголовок задачи")
                return
            due = self.due_var.get().strip()
            if due:
                try:
                    datetime.datetime.strptime(due, DATE_FORMAT)
                except Exception:
                    messagebox.showinfo("Ошибка","Неверный формат даты")
                    return
            task["title"] = title
            task["due"] = due
            task["priority"] = self.prio_var.get()
            task["desc"] = self.desc_text.get("1.0","end").strip()
            self.cur.execute("UPDATE tasks SET title=?, due=?, priority=?, desc=? WHERE id=?", (task["title"], task["due"], task["priority"], task["desc"], task["id"]))
            self.conn.commit()
            self.update_view()
            self.clear_inputs()
            self.status_var.set("Изменение сохранено (автосохранено)")
        save_btn = ttk.Button(self.root, text="Сохранить изменение", command=save_edit)
        save_btn.grid(row=4, column=0, sticky="e", padx=10, pady=(6,6))

    def delete_task(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Инфо","Выберите задачу для удаления")
            return
        try:
            idx = int(sel[0]) - 1
        except:
            idx = 0
        if idx < 0 or idx >= len(self.tasks):
            messagebox.showinfo("Инфо","Неверный выбор")
            return
        removed = self.tasks.pop(idx)
        self.cur.execute("DELETE FROM tasks WHERE id=?", (removed["id"],))
        self.conn.commit()
        self.update_view()
        self.status_var.set("Задача удалена (автосохранено)")

    def toggle_complete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Инфо","Выберите задачу")
            return
        item_id = int(sel[0])
        for t in self.tasks:
            if t["id"]==item_id:
                t["done"] = not t.get("done", False)
                break
        self.update_view()
        self.status_var.set("Статус изменён (не всегда сохраняется)")

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if not path:
            return
        try:
            with open(path,"w",encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
            self.status_var.set(f"Экспортировано в {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not path:
            return
        try:
            with open(path,encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                title = item.get("title","")
                due = item.get("due","")
                prio = item.get("priority","Средний")
                desc = item.get("desc","")
                done = 1 if item.get("done") else 0
                created = item.get("created") or datetime.datetime.now().isoformat()
                self.cur.execute("INSERT INTO tasks (title,due,priority,desc,done,created) VALUES (?,?,?,?,?,?)", (title, due, prio, desc, done, created))
            self.load_from_db()
            self.status_var.set("Импорт выполнен (автосохранено)")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def load_from_db(self):
        self.cur.execute("SELECT id,title,due,priority,desc,done,created FROM tasks ORDER BY id")
        rows = self.cur.fetchall()
        self.tasks = []
        for r in rows:
            self.tasks.append({
                "id": r[0],
                "title": r[1],
                "due": r[2],
                "priority": r[3],
                "desc": r[4],
                "done": bool(r[5]),
                "created": r[6]
            })
        self.update_view()
        self.status_var.set(f"Загружено {len(self.tasks)} задач (из SQLite)")

    def update_view(self, items=None):
        for i in self.tree.get_children():
            self.tree.delete(i)
        source = items if items is not None else self.tasks
        for t in source:
            status = "Выполнено" if t.get("done") else "Невыполнено"
            self.tree.insert("", "end", iid=str(t["id"]), values=(t.get("title",""), t.get("due",""), t.get("priority",""), status))

    def clear_inputs(self):
        self.title_var.set("")
        self.due_var.set("")
        self.prio_var.set("Средний")
        self.desc_text.delete("1.0","end")

    def apply_filter(self):
        f = self.filter_var.get()
        now = datetime.date.today()
        if f=="Все":
            self.update_view()
            return
        if f=="Выполненные":
            items = [t for t in self.tasks if t.get("done")]
        elif f=="Невыполненные":
            items = [t for t in self.tasks if not t.get("done")]
        elif f=="Высокий приоритет":
            items = [t for t in self.tasks if t.get("priority")=="Высокий"]
        elif f=="Просроченные":
            items = []
            for t in self.tasks:
                due = t.get("due")
                if due:
                    try:
                        d = datetime.datetime.strptime(due, DATE_FORMAT).date()
                        if d < now and not t.get("done"):
                            items.append(t)
                    except:
                        pass
        else:
            items = self.tasks
        self.update_view(items)

    def reset_filter(self):
        self.filter_var.set("Все")
        self.update_view()

    def search_tasks(self):
        q = self.search_var.get().strip()
        if not q:
            self.update_view()
            return
        items = [t for t in self.tasks if t.get("title","").startswith(q)]
        self.update_view(items)

    def sort_tasks(self):
        def keyfn(t):
            d = t.get("due")
            try:
                return datetime.datetime.strptime(d, DATE_FORMAT) if d else datetime.datetime.max
            except:
                return datetime.datetime.max
        self.tasks.sort(key=keyfn)
        self.update_view()
        self.status_var.set("Отсортировано (в памяти)")

    def on_close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except:
            pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = TaskManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()
