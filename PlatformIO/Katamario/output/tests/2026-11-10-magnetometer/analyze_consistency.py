import numpy as np, json
from pathlib import Path
root=Path(__file__).parent

def load(name):
    q=None; pairs=[]
    for line in (root/name).read_text().splitlines():
        a=line.split(',')
        if a[0]=='K3' and a[2]=='ready':
            q=np.array(list(map(float,a[5:9]))); q/=np.linalg.norm(q); ms=int(a[1])
        elif a[0]=='# MAG' and a[2]=='0' and q is not None and abs(int(a[1])-ms)<50:
            w,x,y,z=q
            R=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
            pairs.append((int(a[1]),R,list(map(float,a[4:7]))))
    return np.array([p[0] for p in pairs]),np.array([p[1] for p in pairs]),np.array([p[2] for p in pairs])

def fit(R,M):
    # Constant world field + constant affine sensor transform, alternating least squares.
    best=None;rng=np.random.default_rng(42)
    for _ in range(20):
        h=rng.normal(size=3);h/=np.linalg.norm(h)
        for __ in range(70):
            body=np.einsum('nji,j->ni',R,h)
            coef=np.linalg.lstsq(np.column_stack([body,np.ones(len(body))]),M,rcond=None)[0]
            C=coef[:3].T;b=coef[3]
            design=np.einsum('ij,nkj->nik',C,R).reshape(-1,3)
            h=np.linalg.lstsq(design,(M-b).reshape(-1),rcond=None)[0];h/=np.linalg.norm(h)
        pred=np.einsum('nji,j->ni',R,h)@coef[:3]+b
        rms=np.sqrt(np.mean(np.sum((M-pred)**2,axis=1)))
        if best is None or rms<best[0]:best=(rms,h,coef)
    return best

ms,R,M=load('capture-axes.log')
# Reduce overrepresentation of identical resting orientations.
key=np.round(R.reshape(-1,9)/.08).astype(int);_,idx=np.unique(key,axis=0,return_index=True);idx=np.sort(idx)
R=R[idx];M=M[idx];ms=ms[idx]
cut=int(len(M)*.7);rms,h,c=fit(R[:cut],M[:cut]);pred=np.einsum('nji,j->ni',R,h)@c[:3]+c[3]
report={'orientation_bins':len(M),'training_samples':cut,'train_vector_rms_uT':float(rms),'heldout_vector_rms_uT':float(np.sqrt(np.mean(np.sum((M[cut:]-pred[cut:])**2,axis=1)))),'constant_field_baseline_heldout_rms_uT':float(np.sqrt(np.mean(np.sum((M[cut:]-M[:cut].mean(0))**2,axis=1)))),'affine_condition':float(np.linalg.cond(c[:3])),'bias_diagnostic_only':c[3].tolist()}
t,Q,S=load('stationary.log');report['stationary_samples']=len(S);report['stationary_mean_uT']=S.mean(0).tolist();report['stationary_std_uT']=S.std(0).tolist();report['stationary_span_uT']=np.ptp(S,axis=0).tolist()
report['note']='Diagnostic affine fit only. Not a validated calibration; not installed in firmware.'
(root/'consistency-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
