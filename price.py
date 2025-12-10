# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

# --- 1. 網頁基礎設定 ---
st.set_page_config(
    page_title="庫存管理系統",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 常數與路徑設定 ---
DATA_FILE = "inventory_data.csv"
LOG_FILE = "transaction_log.csv"
IMAGE_DIR = "images"

# 確保圖片資料夾存在
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# --- 3. 核心函數區 ---

def load_data():
    """讀取庫存資料"""
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE)
        except:
            pass
    # 若讀取失敗或檔案不存在，回傳空的 DataFrame
    return pd.DataFrame(columns=["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock"])

def load_log():
    """讀取紀錄資料"""
    if os.path.exists(LOG_FILE):
        try:
            return pd.read_csv(LOG_FILE)
        except:
            pass
    return pd.DataFrame(columns=["Time", "User", "Type", "SKU", "Name", "Quantity", "Note"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def save_log(entry):
    df_log = load_log()
    new_entry = pd.DataFrame([entry])
    df_log = pd.concat([df_log, new_entry], ignore_index=True)
    df_log.to_csv(LOG_FILE, index=False)

def save_uploaded_image(uploaded_file, sku):
    """儲存上傳的圖片並回傳檔名"""
    if uploaded_file is None:
        return None
    
    # 取得副檔名 (例如 .jpg)
    file_ext = os.path.splitext(uploaded_file.name)[1]
    # 建立新檔名：SKU + 副檔名
    new_filename = f"{sku}{file_ext}"
    save_path = os.path.join(IMAGE_DIR, new_filename)
    
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return new_filename

# --- 4. 主程式介面 ---

def main():
    # 側邊欄導航 (無須登入)
    with st.sidebar:
        st.title("庫存管理系統")
        st.write("使用者：管理員 (Admin)")
        st.markdown("---")
        
        # 中文選單
        page = st.radio("功能選單", [
            "庫存查詢", 
            "入庫作業", 
            "出庫作業", 
            "品項維護", 
            "異動紀錄"
        ])

    # 根據選擇顯示不同頁面
    if page == "庫存查詢":
        page_search()
    elif page == "入庫作業":
        page_operation("入庫")
    elif page == "出庫作業":
        page_operation("出庫")
    elif page == "品項維護":
        page_maintenance()
    elif page == "異動紀錄":
        page_reports()

# --- 各頁面子程式 ---

def page_search():
    st.subheader("庫存查詢")
    search_term = st.text_input("請輸入 SKU 或 品名關鍵字")
    
    if search_term:
        df = load_data()
        # 轉成字串再比對，避免錯誤
        mask = df['SKU'].astype(str).str.contains(search_term, case=False, na=False) | \
               df['Name'].astype(str).str.contains(search_term, case=False, na=False)
        result = df[mask]
        
        if not result.empty:
            for _, row in result.iterrows():
                with st.container():
                    st.markdown("---")
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        # 圖片顯示 (含防呆機制)
                        img_name = row['ImageFile']
                        if pd.notna(img_name) and str(img_name).strip() != "":
                            img_path = os.path.join(IMAGE_DIR, str(img_name))
                            
                            # 嚴格檢查：必須是檔案存在才顯示
                            if os.path.exists(img_path) and os.path.isfile(img_path):
                                st.image(img_path, width=300)
                            else:
                                st.warning(f"[!] 找不到圖片檔案: {img_name}")
                        else:
                            st.info("未上傳圖片")
                    with c2:
                        st.subheader(row['Name'])
                        st.text(f"SKU: {row['SKU']}")
                        st.text(f"分類: {row['Category']}")
                        st.metric("目前庫存", row['Stock'])
        else:
            st.info("查無資料")

def page_operation(op_type):
    st.subheader(f"{op_type}作業")
    
    # 初始化 session state 用於連續掃描
    if "scan_input" not in st.session_state:
        st.session_state.scan_input = ""

    c1, c2 = st.columns([1, 3])
    qty = c1.number_input(f"{op_type}數量", min_value=1, value=1)
    
    # 定義掃描後的動作
    def on_scan():
        sku_code = st.session_state.scan_box
        if sku_code:
            process_stock(sku_code, qty, op_type)
            st.session_state.scan_box = "" # 清空輸入框以便下一筆

    # 掃描輸入框
    st.text_input("請掃描條碼 (掃描後自動執行)", key="scan_box", on_change=on_scan)

def process_stock(sku, qty, op_type):
    df = load_data()
    match = df[df['SKU'] == sku]
    
    if not match.empty:
        idx = match.index[0]
        current_stock = df.at[idx, 'Stock']
        name = df.at[idx, 'Name']
        
        if op_type == "入庫":
            new_stock = current_stock + qty
        else: # 出庫
            new_stock = current_stock - qty
            
        df.at[idx, 'Stock'] = new_stock
        save_data(df)
        
        # 寫入紀錄
        log = {
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "User": "Admin", # 無登入模式預設為 Admin
            "Type": op_type,
            "SKU": sku,
            "Name": name,
            "Quantity": qty,
            "Note": "掃碼作業"
        }
        save_log(log)
        
        st.success(f"[V] {name} {op_type} {qty} 成功！ (庫存變為: {new_stock})")
    else:
        st.error(f"[X] 找不到此 SKU: {sku}")

def page_maintenance():
    st.subheader("品項維護")
    
    tab_new, tab_edit = st.tabs(["新增商品", "編輯庫存總表"])
    
    with tab_new:
        with st.form("new_prod"):
            c1, c2, c3 = st.columns(3)
            i_code = c1.text_input("編碼 (Code)")
            i_cat = c2.text_input("分類 (Category)")
            i_num = c3.text_input("號碼 (Number)")
            i_name = st.text_input("品名")
            i_file = st.file_uploader("上傳圖片 (選用)", type=["jpg", "png", "jpeg"])
            i_stock = st.number_input("初始庫存", 0)
            
            if st.form_submit_button("儲存商品"):
                sku = f"{i_code}-{i_cat}-{i_num}"
                if i_code and i_name:
                    df = load_data()
                    
                    # 處理圖片
                    fname = None
                    if i_file:
                        fname = save_uploaded_image(i_file, sku)
                    
                    if sku in df['SKU'].values:
                        st.warning("SKU 已存在，將更新資料...")
                        # 若有上傳新圖才更新圖片欄位
                        if fname: 
                            df.loc[df['SKU']==sku, 'ImageFile'] = fname
                        df.loc[df['SKU']==sku, ['Code','Category','Number','Name']] = [i_code,i_cat,i_num,i_name]
                    else:
                        new_row = pd.DataFrame([{
                            "SKU":sku, "Code":i_code, "Category":i_cat, 
                            "Number":i_num, "Name":i_name, 
                            "ImageFile":fname, "Stock":i_stock
                        }])
                        df = pd.concat([df, new_row], ignore_index=True)
                    
                    save_data(df)
                    st.success(f"已儲存: {sku}")
                else:
                    st.error("錯誤：編碼與品名為必填欄位")
                    
    with tab_edit:
        st.caption("提示：點擊表格內容可直接修改，修改完畢請記得按「儲存修改」按鈕。")
        df = load_data()
        # 使用 dynamic 允許增刪列
        edited = st.data_editor(df, num_rows="dynamic", key="main_editor")
        if st.button("儲存修改"):
            save_data(edited)
            st.success("表格資料已更新！")
            time.sleep(1)
            st.rerun()

def page_reports():
    st.subheader("異動紀錄")
    df_log = load_log()
    
    # 篩選功能
    filter_sku = st.text_input("篩選 SKU", key="log_sku")
    if filter_sku:
        df_log = df_log[df_log['SKU'].str.contains(filter_sku, case=False, na=False)]
        
    st.dataframe(df_log.sort_values(by="Time", ascending=False))
    
    # 下載按鈕
    csv = df_log.to_csv(index=False).encode('utf-8-sig')
    st.download_button("下載 CSV 報表", csv, "inventory_log.csv", "text/csv")

if __name__ == "__main__":
    main()
