import asyncio
from prompt_toolkit import Application
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.document import Document

#输入输出独立分区
def build_terminal_ui(submitted_inputs, get_prompt):
    def accept_input(buffer): #回车提交
        submitted_inputs.put_nowait(buffer.text)
        return False
    
    output_area = TextArea(text="", read_only=True, focusable=False)
    input_area = TextArea(height=1, multiline=False, wrap_lines=False, prompt=get_prompt, accept_handler=accept_input)

    hsplit = HSplit([output_area, input_area]) #控件上下摆放
    layout = Layout(hsplit, focused_element=input_area) #布局，键盘输入锚定input_area
    app = Application(layout=layout, full_screen=True) #TUI总控

    return app, output_area

class TerminalWriter: #输出区追加实例
    def __init__(self, output_area): #初始化
        self.output_area = output_area
        self.loop = asyncio.get_running_loop()

    def _append(self, text):
        new_text = self.output_area.text + text 
        self.output_area.buffer.set_document( #界面重绘
            Document(new_text, cursor_position=len(new_text)),
            bypass_readonly=True,
        )

    def write(self, text): #安排追加文字
        if text:
            self.loop.call_soon_threadsafe(self._append, text)
        return len(text)

    def flush(self): #提供调用
        pass