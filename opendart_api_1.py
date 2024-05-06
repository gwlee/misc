#https://gwlee.blogspot.com/2024/05/open-dart-1.html
import xml.etree.ElementTree as ET
# XML 파일 읽기
tree = ET.parse("CORPCODE.xml")
root = tree.getroot()
# 결과를 저장할 딕셔너리 생성
result = {}
# XML 파일의 각 리스트 항목을 순회
for item in root.findall("list"):
  # 회사 이름, 회사 코드, 주식 코드 추출
  corp_name = item.find("corp_name").text
  corp_code = item.find("corp_code").text
  stock_code = item.find("stock_code").text
  # 딕셔너리에 추가
  if stock_code.strip() == '':
    stock_code = '-'
  else:
    pass    
  result[corp_code] = {"corp_name":corp_name, "stock_code": stock_code}
  
ow = open('CORPCODE.txt','w')
for key, value in result.items():
  ow.write(f"{value['stock_code']}\t{value['corp_name']}\t{key}\n")
ow.close()
