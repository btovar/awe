""" resampling procedure for Adaptive Weighted Ensemble from Darve, E. (2011)
The objective is to maintain a number of walkers on each state and update the weights to accelerate convergence """

import numpy as np
import scipy.io
import itertools as it
import os
import shutil
import sys

if __name__ == "__main__":
    # First get the paths and the discrete trajectories to determine where workers ended up
    trajname = 'discrete.traj'
    weightname = 'weight.txt'
    weighthistory = 'weighthistory.txt'
    numstates = 100
    workers = 10
    me = sys.argv[0]
    timestep = int(sys.argv[1])
#    workers  = int(sys.argv[2]) 

    startdir = 'data.%s' % timestep
    startstate = [] # list of start states for all walkers
    endstate = [] # list of end states for all walkers
    walkertopath = [] # list of end directory for all walkers
    weights = [] # list of weights for all walkers
    for top, dir, files in os.walk(startdir):
        for nm in files:
            if nm == trajname:
                traj = np.loadtxt(os.path.join(top,trajname))
                w = np.loadtxt(os.path.join(os.path.join(top,'../'),weightname))
                weights.append(w)
                startstate.append(int(traj[0])) #0-based
                endstate.append(int(traj[-1]))  #0-based
                walkertopath.append(top)
    weights=np.array(weights)
    newweights=[]
    endstate=np.array(endstate)
    wr=np.arange(0,len(weights)) # walker range (cells x walkers / cell)
    er=np.arange(0,numstates) # state range (cells)
    eps = np.finfo(np.double).eps
    list1 = []
    busycells = 0

    if not os.path.exists(weighthistory):
        file(weighthistory, 'w').close()    
    wh = open(weighthistory, "a") 

    for i in er:
        activewlk = 0
        ww = np.where(endstate==i)
        list0 = wr[ww]
        wi = weights[ww]
        ind = np.argsort(-wi)
        list0 = list(list0[ind])
        W = np.sum (wi)
        tw =  W / workers
        print i, " = ", list0, " W = ", W, " tw = ", tw

        if len(list0)>0:
            busycells += 1
            x=list0.pop()
            while True:
                Wx = weights[x]
                if (Wx+eps >= tw):
                    r = int(np.floor( (Wx+eps) / tw ))
#                    print "x= ", x, "r= ", r, " Wx= ", Wx, " tw= ", tw
                    for item in it.repeat(x,r):
                        list1.append(item)
                        newweights.append(tw)
                    activewlk += r
#                    print "residual= ", Wx-r*tw
                    if activewlk < workers and Wx-r*tw+eps > 0.0:
#                        print "adding residual"
                        list0.append(x)
                        weights[x]=Wx-r*tw
                    if len(list0)>0:
                        x=list0.pop()
                    else:
                        break
                else:
                    if len(list0)>0:
                        y = list0.pop()
                        Wy = weights[y]
                        Wxy = Wx + Wy
                        p=np.random.random()
                        if p < Wy / Wxy:
                            x = y
#                        print "chose ", x, " Wxy= ", Wxy
                        weights[x]=Wxy
    # normalize newweights -- roundoff error can make their sum different than 1
    newweights=np.array(newweights)
    newweights /= np.sum(newweights)
    # new workers and new weights are in list1 and newweights
    print "creating output files for timestep %d" % (timestep+1)
    startpdbs = 'startpdbs/'
    if not os.path.exists(startpdbs):
        file(startpdbs,'w').close()
    for root,dirs,files in os.walk(startpdbs):
        for f in files: os.unlink(os.path.join(root, f))
        for d in dirs: shutil.rmtree(os.path.join(root, d))
    # need to write weight%walker.txt with newweights
    # need to write state%walker.xyz with positions
    wh.write(str(timestep)+'\t ')
    for i in er:
        wh.write(str(np.sum(newweights[np.where(endstate[list1]==i)]))+'\t ')
    wh.write('\n')
    wh.close()
    np.savetxt (os.path.join(startpdbs,'busywalkers.txt'), [busycells*workers])  
    for wlk, wt in enumerate(newweights):
        np.savetxt (os.path.join(startpdbs,'weight%d.txt' % wlk), [wt])
        srcpdb = os.path.join(walkertopath[list1[wlk]],'../ala2.pdb')
        dstpdb = os.path.join(startpdbs,'state%d.pdb' % wlk)
        shutil.copy(srcpdb, dstpdb)
        



            


    
                
                


        

    
    
                
    
            
            
            
    

    


