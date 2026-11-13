// Finite-volume unit-square sheet resistance on a conservative copper mask.
// Native grid cells are retained only when all corners lie in filled copper.
// Solve a four-neighbour resistor grid, with equipotential contact patches.
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <queue>
#include <string>
#include <vector>
int main(int argc,char**argv){
 if(argc!=2)return 2;
 std::ifstream in(argv[1]);int nx,ny,ns,nt;double step;
 in>>nx>>ny>>step>>ns>>nt;int nn=nx*ny;std::vector<int>src(ns),dst(nt),fixed(nn,-1);
 for(int&i:src){in>>i;fixed[i]=1;}for(int&i:dst){in>>i;fixed[i]=0;}
 std::vector<char>mask(nn);std::string line;
 for(int y=0;y<ny;y++){in>>line;if((int)line.size()!=nx)return 3;for(int x=0;x<nx;x++)mask[y*nx+x]=line[x]=='1';}
 auto neighbours=[&](int i,auto f){int x=i%nx,y=i/nx;if(x)f(i-1);if(x+1<nx)f(i+1);if(y)f(i-nx);if(y+1<ny)f(i+nx);};
 std::vector<char>connected(nn);std::queue<int>q;
 for(int i:src){if(!mask[i])return 4;connected[i]=1;q.push(i);}
 while(!q.empty()){int i=q.front();q.pop();neighbours(i,[&](int j){if(mask[j]&&!connected[j]){connected[j]=1;q.push(j);}});}
 for(int i:dst)if(!connected[i]){std::cerr<<"Contact disconnected in conservative mask\n";return 5;}
 std::vector<int>index(nn,-1),cells;for(int i=0;i<nn;i++)if(connected[i]&&fixed[i]<0){index[i]=cells.size();cells.push_back(i);}
 int n=cells.size();std::vector<double>diag(n),rhs(n),x(n),r(n),p(n),ap(n),z(n);std::vector<std::vector<int>>adj(n);
 for(int a=0;a<n;a++){int i=cells[a];neighbours(i,[&](int j){if(!connected[j])return;diag[a]++;if(fixed[j]==1)rhs[a]++;else if(fixed[j]<0)adj[a].push_back(index[j]);});}
 auto dot=[&](const auto&a,const auto&b){double s=0;for(int i=0;i<n;i++)s+=a[i]*b[i];return s;};
 auto product=[&](const auto&a,auto&b){for(int i=0;i<n;i++){b[i]=diag[i]*a[i];for(int j:adj[i])b[i]-=a[j];}};
 r=rhs;for(int i=0;i<n;i++)p[i]=z[i]=r[i]/diag[i];double rz=dot(r,z),initial=std::sqrt(dot(rhs,rhs)),relative=1;int iter=0;
 for(;iter<8000&&relative>1e-9;iter++){
  product(p,ap);double den=dot(p,ap);if(den<=0)return 6;double alpha=rz/den;
  for(int i=0;i<n;i++){x[i]+=alpha*p[i];r[i]-=alpha*ap[i];z[i]=r[i]/diag[i];}
  double next=dot(r,z),beta=next/rz;for(int i=0;i<n;i++)p[i]=z[i]+beta*p[i];rz=next;relative=std::sqrt(dot(r,r))/initial;
 }
 if(relative>1e-8)return 7;
 double current=0;for(int i:src)neighbours(i,[&](int j){if(!connected[j])return;double v=fixed[j]<0?x[index[j]]:fixed[j];current+=1-v;});
 std::cout<<std::setprecision(12)<<"{\"grid_mm\":"<<step<<",\"active_unknown_cells\":"<<n<<",\"iterations\":"<<iter<<",\"relative_residual\":"<<relative<<",\"sheet_squares\":"<<1/current;
 for(int kind=0;kind<2;kind++){
  const auto& contacts=kind?dst:src;std::cout<<(kind?",\"sink_current_fractions\":[":",\"source_current_fractions\":[");
  bool first=true;for(int i:contacts){double flux=0;neighbours(i,[&](int j){if(!connected[j])return;double v=fixed[j]<0?x[index[j]]:fixed[j];flux+=kind?v:1-v;});
   if(!first)std::cout<<",";first=false;std::cout<<"["<<i<<","<<flux/current<<"]";
  }std::cout<<"]";
 }std::cout<<"}\n";
}
