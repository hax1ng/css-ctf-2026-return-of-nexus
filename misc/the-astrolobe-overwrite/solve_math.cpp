#include <cstdio>
#include <cstdint>
#include <vector>
#include <thread>
#include <atomic>
#include <algorithm>

static constexpr uint32_t P=65521;
static uint16_t F[P], inv[P], sq[P], curve[P];
static std::vector<std::pair<uint16_t,uint16_t>> points;
static std::atomic<unsigned> found{0};

static inline uint32_t mod(int64_t v) { int64_t r=v%P; return r<0?r+P:r; }
static inline uint16_t transform(uint16_t a) {
    uint32_t b=(a^0x5aa5)%P;
    uint32_t q=1;
    for(int i=0;i<17;i++) q=(q*b)%P;
    uint16_t z=uint16_t((q<<7)|(q>>9));
    return (z^0x1337)%P;
}
static void worker(unsigned id,unsigned threads) {
    for(unsigned pi=id;pi<points.size() && !found;pi+=threads) {
        auto [u,v]=points[pi];
        uint32_t u2=sq[u], v2=sq[v];
        uint32_t k=(u+12506+P-v2)%P;
        for(uint32_t x0=0;x0<P;x0++) {
            uint32_t t=(u2+x0*v+P-40414)%P;
            uint32_t a1=(u+P-x0)%P;
            uint32_t x1=F[a1];
            if(!x1) continue;
            uint32_t w=(k*inv[x1])%P;
            if(sq[t]!=curve[w]) continue;
            uint32_t a2=(v+P-x1)%P;
            uint32_t x2=F[a2];
            if((sq[w]+x2*t+P-v)%P!=4535) continue;
            uint32_t a3=(w+P-x2)%P;
            uint32_t x3=F[a3];
            if((sq[t]+x3*u+P-w)%P!=39941) continue;
            uint32_t a0=(t+P-x3)%P;
            if(F[a0]!=x0) continue;
            if(sq[v] != ((uint64_t(sq[u])+17)*u+43)%P) continue;
            if(sq[t] != ((uint64_t(sq[w])+17)*w+43)%P) continue;
            ++found;
            printf("SOLUTION a=%u,%u,%u,%u x=%u,%u,%u,%u uvwt=%u,%u,%u,%u\n", a0,a1,a2,a3,x0,x1,x2,x3,u,v,w,t);
            fflush(stdout);
        }
        if((pi-id)%(threads*512)==0) { fprintf(stderr,"thread %u point %u/%zu\n",id,pi,points.size()); fflush(stderr); }
    }
}
int main() {
    for(uint32_t i=0;i<P;i++) {
        F[i]=transform(i);
        sq[i]=(uint64_t(i)*i)%P;
        curve[i]=((uint64_t(sq[i])+17)*i+43)%P;
        inv[i]=i?uint16_t(1):0;
    }
    // Linear-time inversion table for the prime field.
    for(uint32_t i=2;i<P;i++) inv[i]=P-(uint64_t(P/i)*inv[P%i])%P;
    std::vector<std::vector<uint16_t>> roots(P);
    for(uint32_t v=0;v<P;v++) roots[sq[v]].push_back(v);
    for(uint32_t u=0;u<P;u++) for(auto v:roots[curve[u]]) points.push_back({uint16_t(u),v});
    fprintf(stderr,"points=%zu\n",points.size());
    unsigned threads=20; std::vector<std::thread> ts;
    for(unsigned i=0;i<threads;i++) ts.emplace_back(worker,i,threads);
    for(auto &t:ts)t.join();
    printf("found=%u\n",unsigned(found));
}
