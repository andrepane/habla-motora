"""One-to-one maximum-cardinality, then maximum-IoU matching (no greedy shortcut)."""
import numpy as np


def overlap(a,b):return max(0,min(a['end_sample_exclusive'],b['end_sample_exclusive'])-max(a['start_sample'],b['start_sample']))
def iou(a,b):
    intersect=overlap(a,b)
    return intersect/(a['end_sample_exclusive']-a['start_sample']+b['end_sample_exclusive']-b['start_sample']-intersect)


def matching(candidates,references,threshold):
    # Successive shortest augmenting paths on a residual bipartite graph.
    nc,nr=len(candidates),len(references);sink=nc+nr+1;graph=[[] for _ in range(sink+1)]
    def edge(a,b,cost):
        graph[a].append([b,1,cost,len(graph[b])]);graph[b].append([a,0,-cost,len(graph[a])-1])
    for i in range(nc):edge(0,1+i,0)
    for j in range(nr):edge(1+nc+j,sink,0)
    for i,c in enumerate(candidates):
        for j,r in enumerate(references):
            score=iou(c,r)
            if score>=threshold:edge(i+1,nc+j+1,-(min(nc,nr)+1+score))
    while True:
        dist=[float('inf')]*(sink+1);dist[0]=0;parent=[None]*(sink+1)
        for _ in range(sink):
            changed=False
            for a,edges in enumerate(graph):
                if not np.isfinite(dist[a]):continue
                for k,(b,cap,cost,_) in enumerate(edges):
                    if cap and dist[b]>dist[a]+cost+1e-12:dist[b]=dist[a]+cost;parent[b]=(a,k);changed=True
            if not changed:break
        if parent[sink] is None:break
        at=sink
        while at:
            a,k=parent[at];e=graph[a][k];e[1]-=1;graph[at][e[3]][1]+=1;at=a
    pairs=[]
    for i in range(nc):
        for b,cap,cost,rev in graph[i+1]:
            if nc+1<=b<=nc+nr and cap==0:pairs.append((i,b-nc-1))
    return pairs


def evaluate(candidates,references,rate,selected_samples,threshold=.3):
    pairs=matching(candidates,references,threshold);tp=len(pairs);fp=len(candidates)-tp;fn=len(references)-tp
    def relevant(c,r):return overlap(c,r)>=.02*rate and overlap(c,r)>=.2*(r['end_sample_exclusive']-r['start_sample'])
    return dict(reference_count=len(references),candidate_count=len(candidates),tp=tp,fp=fp,fn=fn,
        recall=tp/len(references) if references else None,precision=tp/len(candidates) if candidates else None,
        false_candidates_per_minute=fp/(selected_samples/rate/60),
        iou=[iou(candidates[i],references[j]) for i,j in pairs],
        start_error_ms=[1000*(candidates[i]['start_sample']-references[j]['start_sample'])/rate for i,j in pairs],
        end_error_ms=[1000*(candidates[i]['end_sample_exclusive']-references[j]['end_sample_exclusive'])/rate for i,j in pairs],
        fusion_count=sum(sum(relevant(c,r) for r in references)>1 for c in candidates),
        fragmentation_count=sum(sum(relevant(c,r) for c in candidates)>1 for r in references),omissions=fn,
        matches=[dict(candidate_index=i,reference_index=j) for i,j in pairs],threshold_iou=threshold)
