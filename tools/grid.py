import numpy as np
# Miller sheet boundaries on the scan; Talbert segment n = Miller sheet n+1
EDGES=[470,2632,4905,7401,9658,11893,14084,16458,18606,20961,23552,26000]
def col_of(x):
    """return (talbert_segment, column 1..5, fractional) or None"""
    for s in range(11):
        a,b=EDGES[s],EDGES[s+1]
        if a<=x<b:
            f=(x-a)/(b-a); return s+1, min(5,int(f*5)+1), f
    return None
def col_box(seg,col):
    a,b=EDGES[seg-1],EDGES[seg]; w=(b-a)/5
    return a+(col-1)*w, a+col*w
