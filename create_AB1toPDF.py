import glob
import os
import matplotlib.pyplot as plt
import numpy as np
from Bio import SeqIO
from matplotlib.backends.backend_pdf import PdfPages

# 글로벌 시각화 설정 상수
MAX_WIDTH = 900       # 한 줄(subplot)에 표시할 최대 피크 데이터 개수
COUNT_FIG = 3         # 한 페이지에 배치할 subplot 개수
BASE_Y_LIMIT = 3500   # 피크 그래프의 Y축 최대치


def read_ab1_file(file_path):
    """1. 데이터 로드 함수"""
    record = next(SeqIO.parse(file_path, "abi"))
    ra = record.annotations['abif_raw']
    
    trace_data = {
        'G': ra.get('DATA9', []),
        'A': ra.get('DATA10', []),
        'T': ra.get('DATA11', []),
        'C': ra.get('DATA12', [])
    }
    
    pbas_raw = ra.get('PBAS2', b'')
    sequence = pbas_raw.decode('utf-8') if isinstance(pbas_raw, bytes) else str(pbas_raw)
    
    peak_locations = ra.get('PLOC2', [])
    
    if 'phred_quality' in record.letter_annotations:
        quality_scores = record.letter_annotations['phred_quality']
    else:
        pcon2_raw = ra.get('PCON2', b'')
        quality_scores = [int(x) for x in pcon2_raw]
        
    smpl_raw = ra.get('SMPL1', b'')
    sample_name = smpl_raw.decode('utf-8').strip() if isinstance(smpl_raw, bytes) else str(smpl_raw)
    
    metadata = {
        'sample_name': sample_name if sample_name else "Unknown",
        'run_start': record.annotations.get('run_start', 'Unknown Date'),
        'machine_model': record.annotations.get('machine_model', 'ABI Instrument'),
        'lane': ra.get('LANE1', 1)
    }
    
    return trace_data, sequence, peak_locations, quality_scores, metadata


def calculate_quality_metrics(quality_scores):
    """2. 품질 분석 함수"""
    if not quality_scores:
        return 0, 0, (0, 0)
        
    total_bases = len(quality_scores)
    qv20_count = sum(1 for q in quality_scores if q >= 20)
    qv20_ratio = (qv20_count / total_bases) * 100 if total_bases > 0 else 0
    
    max_len = 0
    current_len = 0
    start_idx = 0
    best_range = (0, 0)
    
    for i, q in enumerate(quality_scores):
        if q >= 20:
            if current_len == 0:
                start_idx = i
            current_len += 1
            if current_len > max_len:
                max_len = current_len
                best_range = (start_idx + 1, i + 1)
        else:
            current_len = 0
            
    return qv20_count, qv20_ratio, best_range


def get_base_color(base):
    """3. 염기별 색상 매핑 함수"""
    mapping = {'G': 'k', 'A': 'g', 'T': 'r', 'C': 'b'}
    return mapping.get(base, 'gray')


def draw_report_header(fig, file_name, seq_len, qv20_count, qv20_ratio, best_range, metadata):
    """4. 상단 메타데이터 및 로고 렌더링 함수"""
    fig.text(0.32, 0.96, f'File Name: {file_name}', weight='bold', fontsize=11)
    fig.text(0.32, 0.925, f'Sample Name: {metadata["sample_name"]}', fontsize=11)
    fig.text(0.32, 0.89, f'Run Info: {metadata["run_start"]}', fontsize=11)
    
    fig.text(0.65, 0.96, f'Total Length: {seq_len} bp', fontsize=11)
    fig.text(0.65, 0.925, f'QV20+ Bases: {qv20_count} ({qv20_ratio:.1f}%)', fontsize=11, 
             color='blue' if qv20_ratio >= 70 else 'orange')
    fig.text(0.65, 0.89, f'High Quality Range: {best_range[0]} - {best_range[1]} bp', fontsize=11)

    logo_path = "YOUR_BRAND_LOGO.png"
    fig_height_pixels = fig.bbox.height
    if os.path.exists(logo_path):
        logo = plt.imread(logo_path)
        logo_height_pixels = logo.shape[0]
        fig.figimage(logo, xo=30, yo=fig_height_pixels - logo_height_pixels - 30)
    else:
        fig.text(0.04, 0.93, '[ ANALYSIS REPORT ]', fontsize=15, weight='bold', color='navy')


def draw_report_footer(fig, page_num, total_pages, metadata):
    """5. 하단 풋터 렌더링 함수"""
    fig.text(0.04, 0.015, f'Instrument Model: {metadata["machine_model"]} (Lane: {metadata["lane"]})', fontsize=10, weight='light')
    fig.text(0.82, 0.015, f'Page {page_num} of {total_pages}', fontsize=10, weight='light')


def plot_chromatogram_axis(ax, trace_data, start_idx, end_idx):
    """6. 개별 서열 피크(크로마토그램) 플로팅 함수"""
    t = np.arange(0, end_idx - start_idx, 1)
    
    ax.plot(t, trace_data['G'][start_idx:end_idx], 'k', label='G', linewidth=0.75)
    ax.plot(t, trace_data['A'][start_idx:end_idx], 'g', label='A', linewidth=0.75)
    ax.plot(t, trace_data['T'][start_idx:end_idx], 'r', label='T', linewidth=0.75)
    ax.plot(t, trace_data['C'][start_idx:end_idx], 'b', label='C', linewidth=0.75)
    
    ax.set_xlim(0, MAX_WIDTH)
    
    # [수정] 박스 높이가 줄어들었으므로, Y축 최대 범위를 4900으로 조정하여 시각적 밸런스 유지
    ax.set_ylim(-200, 4900)
    ax.axis('off')


def process_single_ab1(file_name):
    print(f"변환 시작: {file_name}")
    output_pdf_name = file_name[:-4] + '.pdf'
    
    trace_data, sequence, peak_locations, quality_scores, metadata = read_ab1_file(file_name)
    qv20_count, qv20_ratio, best_range = calculate_quality_metrics(quality_scores)
    
    base_peak_len = len(trace_data['G'])
    fig_count = (base_peak_len // MAX_WIDTH) + (1 if base_peak_len % MAX_WIDTH != 0 else 0)
    total_pages = (fig_count // COUNT_FIG) + (1 if fig_count % COUNT_FIG != 0 else 0)
    
    trace_idx = 0
    global_base_idx = 0
    qv_working_list = list(quality_scores)
    
    with PdfPages(output_pdf_name) as pdf:
        for page in range(total_pages):
            fig = plt.figure(figsize=(11.69, 8.27))
            fig.subplots_adjust(left=0.04, top=0.82, bottom=0.05, right=0.96)
            
            draw_report_header(fig, file_name, len(sequence), qv20_count, qv20_ratio, best_range, metadata)
            draw_report_footer(fig, page + 1, total_pages, metadata)
            
            current_page_figs = min(COUNT_FIG, fig_count - (page * COUNT_FIG))
            
            for f_local in range(COUNT_FIG):
                if f_local >= current_page_figs:
                    continue
                
                ax = fig.add_subplot(COUNT_FIG, 1, f_local + 1)
                
                start_p = MAX_WIDTH * trace_idx
                end_p = min(MAX_WIDTH * (trace_idx + 1), base_peak_len)
                
                plot_chromatogram_axis(ax, trace_data, start_p, end_p)
                
                while global_base_idx < len(peak_locations):
                    p_loc = peak_locations[global_base_idx]
                    if start_p <= p_loc < end_p:
                        rel_pos = p_loc - start_p
                        base_char = sequence[global_base_idx]
                        qv = qv_working_list[global_base_idx]
                        
                        if qv < 15:
                            bar_color = '#FF4D4D'
                        elif qv >= 20:
                            bar_color = '#4D79FF'
                        else:
                            bar_color = '#FFD633'
                        
                        # 3. 염기서열 문자 (Y: 3600)
                        ax.annotate(base_char, xy=(rel_pos, 3600), fontsize=9, 
                                    color=get_base_color(base_char), ha='center', weight='semibold')
                        
                        # 2. 5단위 서열 개수 숫자 (Y: 4100)
                        if (global_base_idx + 1) % 5 == 0:
                            ax.annotate(str(global_base_idx + 1), xy=(rel_pos, 4100), 
                                        fontsize=8, ha='center', color='dimgray')
                            
                        # 1. Quality Bar (Y: 4450 시작)
                        # [핵심 수정] qv에 곱해지는 배율을 15에서 6.5로 높이 감소
                        ax.bar(rel_pos, qv * 6.5, bottom=4450, width=3.0, color=bar_color, align='center')
                        
                        global_base_idx += 1
                    else:
                        break
                
                trace_idx += 1
            
            pdf.savefig(fig) 
            plt.close(fig)
            
    print(f"변환 완료: {output_pdf_name}")


if __name__ == "__main__":
    ab1_files = glob.glob('*.ab1')
    if not ab1_files:
        print("현재 디렉토리에 변환할 .ab1 파일이 존재하지 않습니다.")
    else:
        for file in ab1_files:
            try:
                process_single_ab1(file)
            except Exception as e:
                print(f"파일 변환 중 예외 발생 ({file}): {e}")
