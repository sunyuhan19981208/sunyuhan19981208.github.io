"""Author static equation fragments; ordinary Hugo builds need no math runtime."""
from pathlib import Path
import html, json, subprocess

ROOT=Path(__file__).resolve().parents[1]
def main():
    equations=json.loads((ROOT/'editorial/equations.json').read_text(encoding='utf-8'))
    jobs=[dict(key=key,tex=value['tex'],display=True) for key,value in equations.items()]
    temporary=ROOT/'.tools/editorial-math';temporary.mkdir(parents=True,exist_ok=True)
    inputs,outputs=temporary/'input.json',temporary/'output.json'
    inputs.write_text(json.dumps(jobs),encoding='utf-8')
    subprocess.run(['node',str(ROOT/'scripts/render_math.cjs'),str(inputs),str(outputs)],check=True)
    rendered=json.loads(outputs.read_text(encoding='utf-8'))
    destination=ROOT/'editorial/equations';destination.mkdir(parents=True,exist_ok=True)
    for key,value in equations.items():
        tex=html.escape(value['tex'],quote=True)
        svg=rendered[key].replace('<svg ','<svg aria-hidden="true" focusable="false" ')
        markup=(f'<div class="equation-block" id="{key}"><div class="equation-formula" tabindex="0">'
                f'<div class="math-display" role="math" aria-label="{tex}" data-tex="{tex}">{svg}'
                f'<span class="math-source-text" aria-hidden="true">{tex}</span></div></div></div>\n')
        (destination/(key+'.html')).write_text(markup,encoding='utf-8')
    print(f'Prepared {len(equations)} reusable editorial equations.')
if __name__=='__main__':main()
