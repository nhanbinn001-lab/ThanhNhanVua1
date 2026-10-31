import json, threading, time, tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from pynput import mouse, keyboard
except ImportError:
    mouse = keyboard = None

APP_NAME = "Thành Nhân Vua - Macro"

class MacroApp:
    def __init__(self, root):
        self.root = root
        root.title(APP_NAME)
        root.geometry('760x560')
        root.minsize(650, 470)
        self.events = []
        self.recording = False
        self.playing = False
        self.listeners = []
        self.stop_event = threading.Event()
        self.start_time = 0
        self.speed = tk.DoubleVar(value=1.0)
        self.status = tk.StringVar(value='Sẵn sàng')
        self._build()
        root.protocol('WM_DELETE_WINDOW', self.close)

    def _build(self):
        style = ttk.Style()
        try: style.theme_use('clam')
        except Exception: pass
        header = tk.Frame(self.root, bg='#123b70', height=74)
        header.pack(fill='x')
        tk.Label(header, text='THÀNH NHÂN VUA', bg='#123b70', fg='white', font=('Segoe UI', 19, 'bold')).pack(anchor='w', padx=22, pady=(12,0))
        tk.Label(header, text='MACRO DESKTOP • Ghi và phát lại thao tác cục bộ', bg='#123b70', fg='#d8eaff', font=('Segoe UI', 9)).pack(anchor='w', padx=24)
        bar = ttk.Frame(self.root, padding=14); bar.pack(fill='x')
        self.rec_btn = ttk.Button(bar, text='● Bắt đầu ghi', command=self.start_record); self.rec_btn.pack(side='left', padx=(0,8))
        self.stop_rec_btn = ttk.Button(bar, text='■ Dừng ghi', command=self.stop_record, state='disabled'); self.stop_rec_btn.pack(side='left', padx=8)
        self.play_btn = ttk.Button(bar, text='▶ Phát một lần', command=self.play_once); self.play_btn.pack(side='left', padx=8)
        self.stop_btn = ttk.Button(bar, text='Tạm dừng', command=self.stop_play, state='disabled'); self.stop_btn.pack(side='left', padx=8)
        opts = ttk.LabelFrame(self.root, text='Tùy chỉnh', padding=12); opts.pack(fill='x', padx=14)
        ttk.Label(opts, text='Tốc độ phát:').pack(side='left')
        ttk.Scale(opts, from_=0.25, to=2.0, variable=self.speed, orient='horizontal', length=220).pack(side='left', padx=10)
        self.speed_label = ttk.Label(opts, text='1.00×'); self.speed_label.pack(side='left')
        self.speed.trace_add('write', lambda *_: self.speed_label.config(text=f'{self.speed.get():.2f}×'))
        panel = ttk.LabelFrame(self.root, text='Danh sách thao tác', padding=10); panel.pack(fill='both', expand=True, padx=14, pady=12)
        self.listbox = tk.Listbox(panel, font=('Consolas', 9), activestyle='none')
        self.listbox.pack(fill='both', expand=True, side='left')
        sb = ttk.Scrollbar(panel, orient='vertical', command=self.listbox.yview); sb.pack(side='right', fill='y'); self.listbox.config(yscrollcommand=sb.set)
        foot = ttk.Frame(self.root, padding=(14,0,14,12)); foot.pack(fill='x')
        ttk.Button(foot, text='Lưu macro', command=self.save_macro).pack(side='left')
        ttk.Button(foot, text='Mở macro', command=self.load_macro).pack(side='left', padx=8)
        ttk.Button(foot, text='Xóa danh sách', command=self.clear).pack(side='left')
        ttk.Label(foot, textvariable=self.status).pack(side='right')
        ttk.Label(self.root, text='Chỉ ghi/phát thao tác chuột và bàn phím trên máy tính. Không có đăng nhập Discord, token, gửi tin nhắn tự động hoặc lặp vô hạn.', foreground='#555', wraplength=700).pack(anchor='w', padx=16, pady=(0,12))

    def log(self, text):
        self.root.after(0, lambda: (self.listbox.insert('end', text), self.listbox.yview('end')))

    def start_record(self):
        if mouse is None:
            messagebox.showerror('Thiếu thư viện', 'Hãy cài thư viện bằng install.bat trước.'); return
        self.events=[]; self.listbox.delete(0,'end'); self.recording=True; self.start_time=time.monotonic()
        def add(kind, data):
            if self.recording:
                self.events.append({'t': time.monotonic()-self.start_time, 'kind':kind, 'data':data})
        ml = mouse.Listener(on_click=lambda x,y,b,p: add('click', {'x':x,'y':y,'button':str(b),'pressed':p}), on_scroll=lambda x,y,dx,dy: add('scroll', {'x':x,'y':y,'dx':dx,'dy':dy}))
        kl = keyboard.Listener(on_press=lambda k: add('key_down', {'key':str(k)}), on_release=lambda k: add('key_up', {'key':str(k)}))
        self.listeners=[ml,kl]; ml.start(); kl.start()
        self.rec_btn.config(state='disabled'); self.stop_rec_btn.config(state='normal'); self.status.set('Đang ghi…')
        self.log('--- Bắt đầu ghi ---')

    def stop_record(self):
        self.recording=False
        for listener in self.listeners:
            try: listener.stop()
            except Exception: pass
        self.listeners=[]
        self.rec_btn.config(state='normal'); self.stop_rec_btn.config(state='disabled'); self.status.set(f'Đã ghi {len(self.events)} thao tác')
        self.log(f'--- Dừng ghi: {len(self.events)} thao tác ---')

    def play_once(self):
        if self.recording: self.stop_record()
        if self.playing: return
        if not self.events: messagebox.showinfo('Macro trống','Hãy ghi thao tác trước.'); return
        if not messagebox.askyesno('Xác nhận phát macro','Macro sẽ điều khiển chuột và bàn phím trên máy tính đúng một lần. Tiếp tục?'): return
        self.playing=True; self.stop_event.clear(); self.play_btn.config(state='disabled'); self.stop_btn.config(state='normal'); self.status.set('Đang phát…')
        threading.Thread(target=self._play_worker, daemon=True).start()

    def _play_worker(self):
        try:
            from pynput import mouse, keyboard
            m=mouse.Controller(); k=keyboard.Controller(); prev=0
            for ev in self.events:
                if self.stop_event.is_set(): break
                delay=max(0, (ev['t']-prev)/max(.25,self.speed.get()))
                if self.stop_event.wait(delay): break
                d=ev['data']; kind=ev['kind']
                if kind=='click':
                    m.position=(d['x'],d['y']); btn=mouse.Button.left if 'left' in d['button'] else mouse.Button.right if 'right' in d['button'] else mouse.Button.middle
                    (m.press if d['pressed'] else m.release)(btn)
                elif kind=='scroll': m.position=(d['x'],d['y']); m.scroll(d['dx'],d['dy'])
                elif kind in ('key_down','key_up'):
                    keyname=d['key']
                    keyobj=getattr(keyboard.Key, keyname.split('.')[-1], None) if keyname.startswith('Key.') else None
                    if keyobj is None and keyname.startswith("'") and keyname.endswith("'"): keyobj=keyname[1:-1]
                    if keyobj is not None: (k.press if kind=='key_down' else k.release)(keyobj)
                prev=ev['t']
        except Exception as e: self.root.after(0, lambda: messagebox.showerror('Lỗi phát macro', str(e)))
        finally:
            self.playing=False
            self.root.after(0, lambda: (self.play_btn.config(state='normal'), self.stop_btn.config(state='disabled'), self.status.set('Đã dừng' if self.stop_event.is_set() else 'Hoàn tất một lượt')))

    def stop_play(self): self.stop_event.set(); self.status.set('Đang dừng…')
    def clear(self):
        if self.recording or self.playing: return
        self.events=[]; self.listbox.delete(0,'end'); self.status.set('Đã xóa macro')
    def save_macro(self):
        if not self.events: messagebox.showinfo('Thông báo','Không có thao tác để lưu.'); return
        path=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('Macro JSON','*.json')],initialfile='thanh_nhan_vua_macro.json')
        if path:
            with open(path,'w',encoding='utf-8') as f: json.dump(self.events,f,ensure_ascii=False,indent=2)
            self.status.set('Đã lưu macro')
    def load_macro(self):
        path=filedialog.askopenfilename(filetypes=[('Macro JSON','*.json')])
        if path:
            try:
                with open(path,encoding='utf-8') as f: data=json.load(f)
                if not isinstance(data,list) or len(data)>10000: raise ValueError('Tệp macro không hợp lệ hoặc quá lớn.')
                self.events=data; self.listbox.delete(0,'end')
                for e in data: self.listbox.insert('end',f"{e['t']:.2f}s  {e['kind']}  {e['data']}")
                self.status.set(f'Đã tải {len(data)} thao tác')
            except Exception as e: messagebox.showerror('Không thể mở macro',str(e))
    def close(self):
        self.stop_event.set()
        if self.recording: self.stop_record()
        self.root.destroy()

if __name__=='__main__':
    root=tk.Tk(); app=MacroApp(root); root.mainloop()
