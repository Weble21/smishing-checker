"""Execute a frozen notebook snapshot and preserve per-cell outputs in the run folder."""
from pathlib import Path
import sys,io,json,hashlib,traceback,contextlib
import nbformat

class Tee(io.StringIO):
    def __init__(self, original): super().__init__(); self.original=original
    def write(self,text): self.original.write(text);self.original.flush();return super().write(text)
    def flush(self):self.original.flush()

def main():
    root=Path(__file__).resolve().parents[1]
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    source=root/'smishing-checker.ipynb'
    notebook=nbformat.read(source,as_version=4)
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    ns={'__name__':'__main__'}
    counter=0
    for index,cell in enumerate(notebook.cells):
        if cell.cell_type!='code':continue
        counter+=1;cell.execution_count=counter
        print(f'EXECUTING CELL {index} {cell.metadata.get("tags",[])}',flush=True)
        tee=Tee(sys.stdout)
        try:
            with contextlib.redirect_stdout(tee):exec(compile(cell.source,f'notebook-cell-{index}','exec'),ns)
        except Exception:
            cell.outputs=[nbformat.v4.new_output('stream',name='stdout',text=tee.getvalue()),nbformat.v4.new_output('error',ename=sys.exc_info()[0].__name__,evalue=str(sys.exc_info()[1]),traceback=traceback.format_exc().splitlines())]
            if 'RUN_DIR' in ns:nbformat.write(notebook,ns['RUN_DIR']/'executed.ipynb')
            raise
        cell.outputs=[nbformat.v4.new_output('stream',name='stdout',text=tee.getvalue())]
        if 'RUN_DIR' in ns:
            nbformat.write(notebook,ns['RUN_DIR']/'executed.ipynb')
            (ns['RUN_DIR']/'notebook_source.sha256').write_text(source_hash,encoding='ascii')
    print('NOTEBOOK FINISHED',ns['RUN_DIR'],flush=True)

if __name__=='__main__':main()
