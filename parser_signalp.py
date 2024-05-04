#https://services.healthtech.dtu.dk/
#~/signalp-4.1/signalp -f all Trinity.fasta.transdecoder_dir/longest_orfs.pep > Trinity.fasta.transdecoder_dir/longest_orfs.signalP

import os,sys

try:
  inputFile = sys.argv[1]
except:
  print ('signalP output File')
  exit(1)

for rec in open(inputFile):
  if rec.strip().startswith('Name='):
    temp = dict()
    temp['Desc'] = '-'
    for r in rec.strip().split():
      if r.strip().find('=') != -1:
        items = r.strip().split('=')
        temp[items[0]] = items[1]
      else:
        if temp['SP'] == "'YES'":
          temp['Desc'] = ' '.join(rec.strip().split()[2:-3])
        else:
          pass

    print ('{}\t{}\t{}\t{}\t{}\t{}'.format(temp['Name'],temp['SP'][1:-1],str(temp['D']),str(temp['D-cutoff']),temp['Networks'],temp['Desc']))
