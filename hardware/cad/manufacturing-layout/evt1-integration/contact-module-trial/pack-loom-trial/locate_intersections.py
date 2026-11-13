"""Read-only localization of findings in the independently saved coupon."""
from pathlib import Path
import sys,json
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
P=Path(__file__).resolve().parent
d=A.openDocument(str(P/'CompletePackLoomTrial.FCStd'))
def bnd(s):
    b=s.optimalBoundingBox(False,False);return[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
out=[]
for name in ('PACK_FACTORY_POWER1','PACK_FACTORY_POWER2','BODY_POWER2','NTC1_SIGNAL','NTC1_RETURN','NTC2_SIGNAL','NTC2_RETURN'):
    q=d.getObject(name).Shape
    for fixed in ('ProposedFlangeTray','MetalBody','RearNutReference','PackGrowthAllowance'):
        s=d.getObject('Context_'+fixed).Shape
        common=q.common(s)
        if common.Volume>1e-7:
            out.append({'wire':name,'part':fixed,'volume_mm3':common.Volume,'common_bounds_mm':bnd(common),
                        'solids':[{'volume_mm3':v.Volume,'bounds_mm':bnd(v)}for v in common.Solids]})
(P/'intersection-locations.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2),flush=True)
