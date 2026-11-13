"""Cold-read actual fixture links and bind the bounded CAD/PCB candidate handoff."""
from pathlib import Path
import hashlib,json,sys
import FreeCAD as App
import Part
ROOT=Path(__file__).resolve().parents[5];sys.path.insert(0,str(ROOT/'tools'))
import build_evt1_dock_lcd_socket_replacement as m
H=Path(__file__).resolve().parent;C=ROOT/'hardware/pcb/evt1/dock-control/lcd-socket-candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads((H/'native-checks.json').read_text());path=H/'JSTSocketReceivedFit.FCStd'
assert sha(path)==r['native_sha256']and sha(Path(m.__file__))==r['builder_sha256']
assert sha(m.RETENTION)==m.RETENTION_SHA
d=App.openDocument(str(path));p=d.JSTSocketReceivedFit
assert abs(float(p.Parameters.Stack)-1)<1e-8
for row in r['fixture_bodies']:
    b=d.getObject(row['name']);assert b and b.Shape.isValid()and len(b.Shape.Solids)==1
    assert abs(b.Shape.Volume-row['volume_mm3'])<1e-6
    bb=b.Shape.optimalBoundingBox(False,False);bounds=[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax]
    assert max(abs(a-b)for a,b in zip(bounds,row['bounds']))<1e-7
links=[o for o in p.Group if o.TypeId=='App::Link'];assert len(links)==14
for o in links:assert o.LinkedObject and o.Shape.isValid()and o.Shape.Solids,o.Name
assert all(s.FullyConstrained for s in d.Objects if s.TypeId=='Sketcher::SketchObject')
assert not d.JST27FLZDrawingDatums.LoadedGeometryKnown
pcbcheck=json.loads((C/'native-checks.json').read_text())
for f,want in pcbcheck['source_sha256'].items():assert sha(C/f)==want,('Changed PCB candidate source',f)
assert pcbcheck['native_DRC_violations']==0 and pcbcheck['complete_system_ERC_violations']==0
peer=json.loads((H/'independent-electrical-review.json').read_text())
assert peer['board_sha256']==pcbcheck['native_board_sha256']and peer['native_DRC_all0']and peer['native_system_ERC_all0']
files=[H/'README.md',H/'provenance.json',H/'native-checks.json',path,Path(__file__),Path(m.__file__),H/'negative-molex/review.json',H/'independent-electrical-review.json']
out={'scope':'Frozen isolated JST electrical candidate and received-fit CAD fixture; not a loaded socket or complete-case fit release','CAD_native_cold_read_valid':True,'native_five_fixture_bodies':True,'external_actual_LCD_retention_links':14,'source_LCD_retention_sha256':m.RETENTION_SHA,'source_bound_electrical_report_sha256':sha(C/'native-checks.json'),'source_bound_electrical_board_sha256':pcbcheck['native_board_sha256'],'files_sha256':{str(f.relative_to(ROOT)):sha(f)for f in files},'loaded_contactplane_or_socket_geometry_known':False,'received_continuity_numbering_and_neutral_route_verified':False,'complete_case_adjustment_range_qualified':False,'full_product_order_ready':False}
(H/'source-manifest.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'fixture_native_sha256':sha(path),'fixture_builder_sha256':sha(Path(m.__file__)),'electrical_report_sha256':sha(C/'native-checks.json'),'manifest_sha256':sha(H/'source-manifest.json')},indent=2),flush=True)
