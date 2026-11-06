"""Constrained DOCX-to-HTML importer. Never emits source HTML or executes macros."""
import io, zipfile, re, html, hashlib, xml.etree.ElementTree as ET
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
def safe_url(s):
    s=s.strip()
    return s if re.match(r'^(https?://|mailto:|tel:|#[A-Za-z])',s,re.I) and not re.search(r'[\x00-\x20]',s) else ''
def convert(raw, media):
    if len(raw)>10*1024*1024: raise ValueError('Word file must be smaller than 10 MB.')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        items=z.infolist()
        if len(items)>1500 or sum(i.file_size for i in items)>40*1024*1024: raise ValueError('Document is too large when expanded.')
        def xml(name):
            b=z.read(name)
            if b'<!DOCTYPE' in b or b'<!ENTITY' in b: raise ValueError('Unsupported XML declarations.')
            return ET.fromstring(b)
        root=xml('word/document.xml'); rel={}
        if 'word/_rels/document.xml.rels' in z.namelist():
            rel={n.get('Id'):(n.get('Target',''),n.get('TargetMode')) for n in xml('word/_rels/document.xml.rels')}
        def image(node):
            out=''
            for blip in node.iter(A+'blip'):
                target,mode=rel.get(blip.get(R+'embed'),('',None))
                if mode=='External' or not target.startswith('media/') or '..' in target: continue
                b=z.read('word/'+target)
                ext='png' if b.startswith(b'\x89PNG\r\n\x1a\n') else 'jpg' if b.startswith(b'\xff\xd8\xff') else 'gif' if b.startswith((b'GIF87a',b'GIF89a')) else 'webp' if b.startswith(b'RIFF') and b[8:12]==b'WEBP' else None
                if ext and len(b)<=8*1024*1024:
                    name=hashlib.sha256(b).hexdigest()+'.'+ext
                    (media/name).write_bytes(b)
                    out+='<img loading="lazy" alt="Image from the imported Word page" src="/media/'+name+'">'
            return out
        def run(n):
            txt=''.join(html.escape(x.text or '') if x.tag==W+'t' else '<br>' if x.tag==W+'br' else ' ' if x.tag==W+'tab' else '' for x in n.iter())+image(n)
            props=n.find(W+'rPr')
            if props is not None:
                for tag,wrap in [('b','strong'),('i','em'),('u','u')]:
                    item=props.find(W+tag)
                    if item is not None and item.get(W+'val') not in ('0','false','none'): txt=f'<{wrap}>'+txt+f'</{wrap}>'
                col=props.find(W+'color')
                if col is not None and re.fullmatch(r'[0-9a-fA-F]{6}',col.get(W+'val','')): txt='<span style="color:#'+col.get(W+'val')+'">'+txt+'</span>'
            return txt
        def paragraph(p):
            text=''
            for n in p:
                if n.tag==W+'r': text+=run(n)
                elif n.tag==W+'hyperlink':
                    inside=''.join(run(r) for r in n if r.tag==W+'r')
                    url=safe_url('#'+n.get(W+'anchor')) if n.get(W+'anchor') else safe_url(rel.get(n.get(R+'id'),('',None))[0])
                    text+=('<a rel="noopener noreferrer" href="'+html.escape(url,quote=True)+'">'+inside+'</a>') if url else inside
            prop=p.find(W+'pPr'); tag='p'; style=''
            if prop is not None:
                h=prop.find(W+'pStyle'); val=h.get(W+'val','') if h is not None else ''
                if re.fullmatch(r'Heading[1-6]',val,re.I): tag='h'+val[-1]
                elif val.lower()=='title': tag='h1'
                align=prop.find(W+'jc')
                if align is not None and align.get(W+'val') in ('left','center','right','both'): style=' style="text-align:'+('justify' if align.get(W+'val')=='both' else align.get(W+'val'))+'"'
                if prop.find(W+'numPr') is not None: text='• '+text
            return f'<{tag}{style}>'+text+f'</{tag}>'
        def block(n):
            if n.tag==W+'p': return paragraph(n)
            if n.tag==W+'tbl': return '<div class="table-scroll"><table>'+''.join('<tr>'+''.join('<td>'+''.join(block(c) for c in cell)+'</td>' for cell in row if cell.tag==W+'tc')+'</tr>' for row in n if row.tag==W+'tr')+'</table></div>'
            return ''
        result=''.join(block(n) for n in root.find(W+'body'))
        if not result.strip(): raise ValueError('No supported page content found.')
        return result
