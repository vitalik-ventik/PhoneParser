import tkinter as tk
import datetime

class DateEntry(tk.Frame):
    def __init__(self, master, default_date, frame_look={}, **look):
        args = dict(relief=tk.SUNKEN, border=1)
        args.update(frame_look)
        tk.Frame.__init__(self, master, **args)

        args = {'relief': tk.FLAT}
        args.update(look)

        self.day_v = tk.StringVar()
        self.month_v = tk.StringVar()
        self.year_v = tk.StringVar()

        self.entry_1 = tk.Entry(self, width=2, textvariable=self.day_v, **args)
        self.label_1 = tk.Label(self, text='.', bg='white', **args)
        self.entry_2 = tk.Entry(self, width=2, textvariable=self.month_v, **args)
        self.label_2 = tk.Label(self, text='.', bg='white', **args)
        self.entry_3 = tk.Entry(self, width=4, textvariable=self.year_v, **args)

        if default_date is not None:
            self.set_date(default_date)

        self.entry_1.pack(side=tk.LEFT)
        self.label_1.pack(side=tk.LEFT)
        self.entry_2.pack(side=tk.LEFT)
        self.label_2.pack(side=tk.LEFT)
        self.entry_3.pack(side=tk.LEFT)

        self.entry_1.bind('<KeyRelease>', self._e1_check)
        self.entry_2.bind('<KeyRelease>', self._e2_check)
        self.entry_3.bind('<KeyRelease>', self._e3_check)

    def set_date(self, new_date):
        if isinstance(new_date, datetime.datetime):
            self.day_v.set(str(new_date.day).zfill(2))
            self.month_v.set(str(new_date.month).zfill(2))
            self.year_v.set(str(new_date.year))
        elif isinstance(new_date, str):
            self.day_v.set(new_date[:2])
            self.month_v.set(new_date[3:5])
            self.year_v.set(new_date[6:10])

    def _backspace(self, entry):
        cont = entry.get()
        entry.delete(0, tk.END)
        entry.insert(0, cont[:-1])

    def _e1_check(self, e):
        cont = self.entry_1.get()
        if len(cont) > 0:
            if len(cont) >= 2:
                self.entry_2.focus()
            
            if len(cont) > 2 or not cont[-1].isdigit():
                self._backspace(self.entry_1)
                self.entry_1.focus()

    def _e2_check(self, e):
        cont = self.entry_2.get()
        if len(cont) > 0:
            if len(cont) >= 2:
                self.entry_3.focus()
            if len(cont) > 2 or not cont[-1].isdigit():
                self._backspace(self.entry_2)
                self.entry_2.focus()

    def _e3_check(self, e):
        cont = self.entry_2.get()
        if len(cont) > 0:
            if len(cont) > 4 or not cont[-1].isdigit():
                self._backspace(self.entry_3)

    def get(self):
        return datetime.datetime(year=int(self.entry_3.get()),
                                 month=int(self.entry_2.get()),
                                 day=int(self.entry_1.get()))

if __name__ == '__main__':
    def show_contents(e):
        print(dentry.get())

    win = tk.Tk()
    win.title('DateEntry demo')

    dentry = DateEntry(win, default_date='28/02/2016', font=('Helvetica', 14, tk.NORMAL), border=1)
    dentry.pack()

    win.bind('<Return>', show_contents)
    win.mainloop()