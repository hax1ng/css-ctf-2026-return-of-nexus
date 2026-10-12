#include <cstdio>
#include <cstdint>

static int h[18][4][4], g[18][4][12];
static int c0[3][18], lv[3][18][4], lo[3][18][12], target[3][18];
static uint8_t mul[17][17], inv[17];
static int mod(int x) { x %= 17; return x < 0 ? x+17 : x; }

int main() {
  for (int a=0;a<17;a++) for (int b=0;b<17;b++) mul[a][b]=(a*b)%17;
  for (int a=1;a<17;a++) for (int b=1;b<17;b++)
    if (mul[a][b]==1) inv[a]=b;
  FILE *f=fopen("numeric.txt","r"); if(!f) return 1;
  for(int j=0;j<18;j++) for(int a=0;a<4;a++) for(int b=0;b<4;b++) fscanf(f,"%d",&h[j][a][b]);
  for(int j=0;j<18;j++) for(int a=0;a<4;a++) for(int b=0;b<12;b++) fscanf(f,"%d",&g[j][a][b]);
  for(int k=0;k<3;k++) {
    for(int j=0;j<18;j++) fscanf(f,"%d",&c0[k][j]);
    for(int j=0;j<18;j++) for(int a=0;a<4;a++) fscanf(f,"%d",&lv[k][j][a]);
    for(int j=0;j<18;j++) for(int b=0;b<12;b++) fscanf(f,"%d",&lo[k][j][b]);
    for(int j=0;j<18;j++) fscanf(f,"%d",&target[k][j]);
  }
  fclose(f);
  for(int k=0;k<3;k++) {
    int count=0;
    for(int v0=0;v0<17;v0++) for(int v1=0;v1<17;v1++)
    for(int v2=0;v2<17;v2++) for(int v3=0;v3<17;v3++) {
      int v[4]={v0,v1,v2,v3};
      uint8_t A[18][13]{};
      for(int j=0;j<18;j++) {
        int rhs=target[k][j]-c0[k][j];
        for(int a=0;a<4;a++) rhs-=lv[k][j][a]*v[a];
        for(int a=0;a<4;a++) for(int b=0;b<4;b++) rhs-=9*h[j][a][b]*v[a]*v[b];
        A[j][12]=mod(rhs);
        for(int b=0;b<12;b++) {
          int val=lo[k][j][b];
          for(int a=0;a<4;a++) val+=v[a]*g[j][a][b];
          A[j][b]=mod(val);
        }
      }
      int pivots[12], rank=0;
      for(int col=0;col<12;col++) {
        int p=-1;
        for(int r=rank;r<18;r++) if(A[r][col]) {p=r;break;}
        if(p<0) continue;
        for(int t=col;t<=12;t++) {uint8_t z=A[rank][t]; A[rank][t]=A[p][t]; A[p][t]=z;}
        uint8_t scale=inv[A[rank][col]];
        for(int t=col;t<=12;t++) A[rank][t]=mul[A[rank][t]][scale];
        for(int r=rank+1;r<18;r++) if(A[r][col]) {
          uint8_t factor=A[r][col]; A[r][col]=0;
          for(int t=col+1;t<=12;t++) {
            int z=A[r][t]-mul[factor][A[rank][t]];
            A[r][t]=z<0?z+17:z;
          }
        }
        pivots[rank++]=col;
      }
      bool ok=true;
      for(int r=rank;r<18;r++) if(A[r][12]) {ok=false;break;}
      if(!ok) continue;
      uint8_t oil[12]{};
      for(int r=rank-1;r>=0;r--) {
        int z=A[r][12];
        for(int t=pivots[r]+1;t<12;t++) z-=mul[A[r][t]][oil[t]];
        oil[pivots[r]]=mod(z);
      }
      printf("block %d rank %d vinegar %d %d %d %d oil", k,rank,v0,v1,v2,v3);
      for(auto q:oil) printf(" %d", q); printf("\n"); fflush(stdout);
      count++;
    }
    fprintf(stderr,"block %d solutions %d\n",k,count);
  }
}
