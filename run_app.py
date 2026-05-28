from __future__ import annotations

import os
import threading
import webbrowser
from json import JSONDecodeError
from pathlib import Path
from tkinter import Tk, StringVar, filedialog, messagebox
from tkinter import ttk

from src.utkino.generator import build_report_from_excel, make_report_dir


ROOT = Path(__file__).resolve().parent


class UtkinoApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Utkino Analytics")
        self.root.geometry("680x330")
        self.root.minsize(620, 300)

        self.selected_file = StringVar(value="")
        self.output_dir = StringVar(value=str(ROOT / "reports"))
        self.status = StringVar(value="Выберите Excel-файл отчета гостиницы.")
        self.report_path: Path | None = None

        self.build_ui()

    def build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        title = ttk.Label(frame, text="Utkino Analytics", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w")

        subtitle = ttk.Label(
            frame,
            text="Выберите Excel-файл и сформируйте HTML-отчет.",
        )
        subtitle.pack(anchor="w", pady=(4, 16))

        file_row = ttk.Frame(frame)
        file_row.pack(fill="x")

        self.file_entry = ttk.Entry(file_row, textvariable=self.selected_file)
        self.file_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(file_row, text="Выбрать Excel", command=self.choose_file).pack(
            side="left",
            padx=(8, 0),
        )

        output_label = ttk.Label(frame, text="Папка для сохранения отчетов")
        output_label.pack(anchor="w", pady=(14, 4))

        output_row = ttk.Frame(frame)
        output_row.pack(fill="x")

        self.output_entry = ttk.Entry(output_row, textvariable=self.output_dir)
        self.output_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(output_row, text="Выбрать папку", command=self.choose_output_dir).pack(
            side="left",
            padx=(8, 0),
        )

        action_row = ttk.Frame(frame)
        action_row.pack(fill="x", pady=(16, 0))

        self.generate_button = ttk.Button(
            action_row,
            text="Сформировать отчет",
            command=self.generate_report,
        )
        self.generate_button.pack(side="left")

        self.open_button = ttk.Button(
            action_row,
            text="Открыть отчет",
            command=self.open_report,
            state="disabled",
        )
        self.open_button.pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill="x", pady=(18, 8))

        ttk.Label(frame, textvariable=self.status, wraplength=560).pack(anchor="w")

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите отчет Excel",
            filetypes=[
                ("Excel files", "*.xls *.xlsx"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.selected_file.set(path)
            self.status.set("Файл выбран. Можно формировать отчет.")
            self.open_button.configure(state="disabled")
            self.report_path = None

    def choose_output_dir(self) -> None:
        path = filedialog.askdirectory(
            title="Выберите папку для сохранения отчетов",
            initialdir=self.output_dir.get() or str(ROOT),
        )
        if path:
            self.output_dir.set(path)
            self.status.set("Папка отчетов выбрана.")

    def generate_report(self) -> None:
        input_path = Path(self.selected_file.get())
        if not input_path.exists():
            messagebox.showwarning("Файл не выбран", "Выберите Excel-файл отчета.")
            return
        output_dir = Path(self.output_dir.get())
        if not output_dir:
            messagebox.showwarning("Папка не выбрана", "Выберите папку для отчетов.")
            return

        self.generate_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.progress.start(12)
        self.status.set("Формирую отчет. Это может занять несколько секунд...")

        thread = threading.Thread(
            target=self._generate_report_worker,
            args=(input_path, output_dir),
            daemon=True,
        )
        thread.start()

    def _generate_report_worker(self, input_path: Path, output_dir: Path) -> None:
        try:
            result = build_report_from_excel(
                input_file=input_path,
                report_dir=make_report_dir(output_dir),
            )
        except Exception as error:
            self.root.after(0, self._generation_failed, self._format_error(error))
            return

        self.root.after(0, self._generation_finished, result)

    def _format_error(self, error: Exception) -> str:
        message = str(error).strip()
        if isinstance(error, PermissionError):
            return (
                "Не удалось записать файлы отчета. Закройте открытый отчет, Excel, "
                "предпросмотр в проводнике или синхронизацию папки и повторите запуск."
            )
        if isinstance(error, FileNotFoundError):
            return (
                "В Excel не найден один из обязательных листов или файл недоступен. "
                "Проверьте, что выбран именно годовой отчет гостиницы."
            )
        if isinstance(error, JSONDecodeError):
            return (
                "Не удалось прочитать служебные данные отчета. Попробуйте выбрать "
                "новую пустую папку для сохранения и сформировать отчет заново."
            )
        if isinstance(error, ValueError):
            return (
                "В отчете есть ячейки в неожиданном формате. Программа попыталась "
                "обработать пустые и некорректные числа как 0, но структура файла "
                "слишком сильно отличается от ожидаемой."
            )
        return message or (
            "Не удалось сформировать отчет. Проверьте, что выбран Excel-файл отчета "
            "и папка сохранения доступна для записи."
        )

    def _generation_finished(self, result: dict) -> None:
        self.progress.stop()
        self.generate_button.configure(state="normal")
        self.open_button.configure(state="normal")
        self.report_path = Path(result["output_path"])
        self.status.set(
            "Отчет готов: "
            f"{self.report_path}. Гостей: {result['summary']['guest_count']}, "
            f"доход: {result['summary']['total_revenue']:,.2f}"
        )

    def _generation_failed(self, message: str) -> None:
        self.progress.stop()
        self.generate_button.configure(state="normal")
        self.status.set("Не удалось сформировать отчет.")
        messagebox.showerror("Ошибка генерации", message)

    def open_report(self) -> None:
        if not self.report_path or not self.report_path.exists():
            messagebox.showwarning("Отчет не найден", "Сначала сформируйте отчет.")
            return
        webbrowser.open(self.report_path.resolve().as_uri())


if __name__ == "__main__":
    os.chdir(ROOT)
    window = Tk()
    app = UtkinoApp(window)
    window.mainloop()
