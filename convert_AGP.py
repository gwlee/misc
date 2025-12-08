#!/bin/python
import sys,os,re
from Bio import SeqIO

try:    
  input_file = sys.argv[1]    
  output_file = sys.argv[2]
except:    
  print "python fasta2agp.py <in.fa> <output_prefix>"
  exit(1)
  
output_agp = "%s.agp" % (output_file)
output_contig = "%s.contig.fa" % (output_file)
o_agp = open(output_agp,"w")
o_contig = open(output_contig,"w")
o_agp.write("""##agp-version\t2.0# ORGANISM:# TAX_ID:# ASSEMBLY NAME:# ASSEMBLY DATE:# GENOME CENTER:# DESCRIPTION:""")
seq_name = []
seq_dict = {}
for rec in SeqIO.parse(open(input_file), format='fasta'):
  name = ((rec.description).strip()).split()[0]
  seq = rec.seq.tostring()
  seq_name.append(name)
  seq_dict[name] = seq

s_temp = []
c_temp = []
for rec in seq_name:
  if rec[0] == "s":
    s_temp.append(int(rec.replace("scaffold","")))
  else:
    c_temp.append(int(rec.replace("C","")))

seq_name = []
s_temp.sort()
c_temp.sort()
for x in s_temp:
  seq_name.append("scaffold%s" % (x))
for x in c_temp:
  seq_name.append("C%s" % (x))

cont=1
for rec in seq_name:
  seq = (seq_dict[rec]).upper()
  sub_len = len(seq)
  tmp_n_List = re.split(r"[ACGT]+[N]{0,9}[A|C|G|T]",seq)
  seq_List = re.split(r"[N]{10,}",seq)
  part_num = 1
  
n_List = []
for empty_item in tmp_n_List:
  if empty_item.count('N') >= 10:
    n_List.append(empty_item.strip())
  else:
    pass

    re_assembly_List = []
    if len(seq_List) == 1:
      re_assembly_List.append((seq_List[0]).strip())
    else:
      if seq[:20].count('N') > 10:
        re_assembly_List.append(n_List[0])
        for i in range(len(n_List)):
          re_assembly_List.append(seq_List[i])
          re_assembly_List.append(n_List[i+1])

      else:
        re_assembly_List.append(seq_List[0])
        for i in range(len(n_List)):
          re_assembly_List.append(n_List[i])
          re_assembly_List.append(seq_List[i+1])


    if len(re_assembly_List) == 1:
      start,end=1,len(re_assembly_List[0])
      o_agp.write("%s\t%s\t%s\t%s\tW\tcontig_%s\t1\t%s\t+\n" % (rec,start,end,part_num,cont,len(re_assembly_List[0])))
      o_contig.write(">contig_%s\n%s\n" % (cont,re_assembly_List[0]))
      cont+=1
    else:
      start,end=1,0
      for contig_item in re_assembly_List:
        end+=len(contig_item)
        if contig_item.count('N') > 10:
          o_agp.write("%s\t%s\t%s\t%s\tN\t%s\tscaffold\tyes\tpaired-ends\n" % (rec,start,end,part_num,len(contig_item)))
          start+=len(contig_item)
            
        else:
          o_agp.write("%s\t%s\t%s\t%s\tW\tcontig_%s\t1\t%s\t+\n" % (rec,start,end,part_num,cont,len(contig_item)))
          o_contig.write(">contig_%s\n%s\n" % (cont,contig_item))
          start+=len(contig_item)
          cont+=1

          part_num+=1

o_agp.close()
o_contig.close()
