package com.hakan.jarvis;
public final class WakeWordGate{
 private final float threshold,strongThreshold;private final long debounceMs;private final boolean[] hitWindow;private final int minHits;private int pos,filled;private long lastDetection;
 public WakeWordGate(float threshold,float strongThreshold,int windowSize,int minHits,long debounceMs){if(windowSize<1||minHits<1||minHits>windowSize)throw new IllegalArgumentException("invalid vote window");this.threshold=threshold;this.strongThreshold=strongThreshold;this.debounceMs=debounceMs;this.hitWindow=new boolean[windowSize];this.minHits=minHits;}
 public synchronized boolean accept(float score,long nowMs){hitWindow[pos]=score>=threshold;pos=(pos+1)%hitWindow.length;if(filled<hitWindow.length)filled++;if(nowMs-lastDetection<debounceMs)return false;boolean strong=score>=strongThreshold;int hits=0;for(int i=0;i<filled;i++)if(hitWindow[i])hits++;boolean voted=filled>=minHits&&hits>=minHits;if(!strong&&!voted)return false;lastDetection=nowMs;clearVotes();return true;}
 public synchronized void reset(){lastDetection=0L;clearVotes();}
 private void clearVotes(){for(int i=0;i<hitWindow.length;i++)hitWindow[i]=false;pos=0;filled=0;}
}
