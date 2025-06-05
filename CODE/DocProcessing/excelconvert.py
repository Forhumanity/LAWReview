import pandas as pd
import json
from datetime import datetime
import os
from collections import defaultdict

def convert_excel_to_json(excel_file_path, output_json_path=None):
    """
    Convert Excel file to JSON format matching the regulation analysis schema
    
    Args:
        excel_file_path (str): Path to the Excel file
        output_json_path (str): Path for output JSON file (optional)
    
    Returns:
        dict: JSON structure matching the schema
    """
    
    # Read Excel file
    try:
        df = pd.read_excel(excel_file_path)
        print(f"Successfully loaded Excel file with {len(df)} rows")
        print("Columns found:", df.columns.tolist())
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None
    
    # Initialize the JSON structure
    json_structure = {
        "文档路径": f"Regufile/{os.path.basename(excel_file_path)}",
        "文档名称": os.path.basename(excel_file_path),
        "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "审查模式": "regulation",
        "LLM分析结果": {}
    }
    
    # Get unique analysts/experts (分析专家)
    if '分析专家' in df.columns:
        analysts = df['分析专家'].dropna().unique()
    else:
        analysts = ['deepseek']  # Default analyst
    
    # Process each analyst
    for analyst in analysts:
        try:
            # Filter data for this analyst
            if '分析专家' in df.columns:
                analyst_df = df[df['分析专家'] == analyst].copy()
            else:
                analyst_df = df.copy()
            
            if len(analyst_df) == 0:
                continue
                
            # Process the analyst data
            analyst_data = process_analyst_data(analyst_df, analyst)
            json_structure["LLM分析结果"][analyst] = analyst_data
            
        except Exception as e:
            # If there's an error, add error information
            json_structure["LLM分析结果"][analyst] = {
                "文档名称": os.path.basename(excel_file_path),
                "分析日期": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "LLM提供商": analyst,
                "LLM模型": f"{analyst}-chat",
                "详细分析": {},
                f"错误_{analyst}": str(e)
            }
    
    # Save to JSON file if output path provided
    if output_json_path:
        try:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(json_structure, f, ensure_ascii=False, indent=2)
            print(f"JSON file saved to: {output_json_path}")
        except Exception as e:
            print(f"Error saving JSON file: {e}")
    
    return json_structure

def process_analyst_data(df, analyst):
    """
    Process analyst-specific data into the required JSON structure
    
    Args:
        df (DataFrame): Data from Excel for specific analyst
        analyst (str): Analyst name
    
    Returns:
        dict: Formatted analyst data
    """
    
    # Get document metadata from first row
    first_row = df.iloc[0]
    
    # Initialize analyst structure
    analyst_data = {
        "文档名称": os.path.basename(first_row.get('法规名称', '')) + '.pdf',
        "分析日期": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "LLM提供商": analyst,
        "LLM模型": f"{analyst}-chat",
        "详细分析": {},
        "文档标题": first_row.get('法规名称', ''),
        "颁布机构": first_row.get('颁布机构', ''),
        "生效日期": "",  # Not provided in Excel structure
        "关键发现": [],
        "合规建议": []
    }
    
    # Process data by major categories (大类要素名称)
    if '大类要素名称' in df.columns:
        categories = df['大类要素名称'].dropna().unique()
        
        for category in categories:
            category_df = df[df['大类要素名称'] == category].copy()
            category_requirements = process_category_requirements(category_df)
            
            # Clean category name for JSON key
            category_key = category.strip()
            analyst_data["详细分析"][category_key] = category_requirements
    
    # Generate key findings and compliance recommendations
    analyst_data["关键发现"] = generate_key_findings(df)
    analyst_data["合规建议"] = generate_compliance_recommendations(df)
    
    return analyst_data

def process_category_requirements(category_df):
    """
    Process requirements for a specific category
    
    Args:
        category_df (DataFrame): DataFrame filtered for specific category
    
    Returns:
        list: List of requirements for the category
    """
    
    requirements = []
    
    for idx, row in category_df.iterrows():
        requirement = {
            "框架要求编号": int(row.get('小类要素编号', idx + 1)),
            "框架要求名称": str(row.get('小类要素名称', '')),
            "法规覆盖情况": str(row.get('法规覆盖情况', '未覆盖')),
            "法规要求内容": [],
            "实施要求": str(row.get('实施要求', '')),
            "处罚措施": str(row.get('处罚措施', ''))
        }
        
        # Create detailed requirement content
        content_entry = {
            "条款编号": str(row.get('条款编号', '')),
            "总体要求": str(row.get('实施要求', '')),  # Using 实施要求 as 总体要求
            "要求建立的制度": str(row.get('要求建立的制度', '')),
            "要求建立的管理体系": str(row.get('要求建立的管理体系', '')),
            "负面清单": str(row.get('负面清单', '')),
            "要求提交的报告": str(row.get('要求提交的报告', '')),
            "要求提供的信息和数据": str(row.get('要求提供的信息和数据', '')),
            "强制等级": str(row.get('强制等级', '强制')),
            "适用对象": str(row.get('适用对象', '中央企业')),
            "原文内容": str(row.get('实施要求', ''))  # Using 实施要求 as original content
        }
        
        requirement["法规要求内容"].append(content_entry)
        requirements.append(requirement)
    
    return requirements

def generate_key_findings(df):
    """
    Generate key findings based on the data
    
    Args:
        df (DataFrame): Input data
    
    Returns:
        list: Key findings
    """
    
    findings = []
    
    # Analyze coverage status
    if '法规覆盖情况' in df.columns:
        coverage_counts = df['法规覆盖情况'].value_counts()
        total_requirements = len(df)
        
        if '完全覆盖' in coverage_counts:
            fully_covered = coverage_counts['完全覆盖']
            findings.append(f"法规中有 {fully_covered} 项要求得到完全覆盖，占总要求的 {fully_covered/total_requirements*100:.1f}%。")
        
        if '部分覆盖' in coverage_counts:
            partially_covered = coverage_counts['部分覆盖']
            findings.append(f"有 {partially_covered} 项要求得到部分覆盖，需要进一步完善相关制度和管理体系。")
        
        if '未覆盖' in coverage_counts:
            not_covered = coverage_counts['未覆盖']
            findings.append(f"有 {not_covered} 项要求未被覆盖，存在合规风险，需要重点关注。")
    
    # Analyze mandatory requirements
    if '强制等级' in df.columns:
        mandatory_count = len(df[df['强制等级'] == '强制'])
        if mandatory_count > 0:
            findings.append(f"法规中包含 {mandatory_count} 项强制性要求，企业必须严格执行。")
    
    # Add specific findings based on categories
    if '大类要素名称' in df.columns:
        categories = df['大类要素名称'].value_counts()
        max_category = categories.index[0]
        findings.append(f"'{max_category}' 类别包含最多要求（{categories.iloc[0]} 项），是监管重点领域。")
    
    return findings[:5]  # Return top 5 findings

def generate_compliance_recommendations(df):
    """
    Generate compliance recommendations based on the data
    
    Args:
        df (DataFrame): Input data
    
    Returns:
        list: Compliance recommendations
    """
    
    recommendations = []
    
    # Recommendations based on coverage gaps
    if '法规覆盖情况' in df.columns:
        uncovered = df[df['法规覆盖情况'] == '未覆盖']
        if len(uncovered) > 0:
            recommendations.append("建议企业针对未覆盖的监管要求，制定专项合规计划，建立相应的管理制度和操作流程。")
        
        partially_covered = df[df['法规覆盖情况'] == '部分覆盖']
        if len(partially_covered) > 0:
            recommendations.append("对于部分覆盖的要求，建议企业完善现有制度，填补管理空白，确保全面合规。")
    
    # Recommendations for system building
    if '要求建立的制度' in df.columns:
        system_requirements = df['要求建立的制度'].dropna()
        if len(system_requirements) > 0:
            recommendations.append("建议企业系统性建立和完善各项管理制度，确保制度的完整性和可操作性。")
    
    # Recommendations for management systems
    if '要求建立的管理体系' in df.columns:
        mgmt_requirements = df['要求建立的管理体系'].dropna()
        if len(mgmt_requirements) > 0:
            recommendations.append("建议建立统一的管理体系架构，实现各项管理要求的有机集成和协同运作。")
    
    # General recommendation
    recommendations.append("建议企业建立定期的合规检查和评估机制，确保各项制度和管理体系的有效执行。")
    
    return recommendations[:5]  # Return top 5 recommendations

# Example usage and testing function
def test_conversion():
    """
    Test function to demonstrate usage
    """
    
    # Create sample data matching the Excel structure
    sample_data = {
        '大类要素名称': ['一、治理与战略', '一、治理与战略', '二、全面风险管理'],
        '小类要素编号': [1, 2, 3],
        '小类要素名称': ['海外业务治理与决策管理', '董事会海外风险监督细则', '海外全面风险管理基本制度'],
        '法规名称': ['中央企业境外投资监督管理办法'] * 3,
        '颁布机构': ['国务院国有资产监督管理委员会'] * 3,
        '分析专家': ['openai', 'deepseek', 'openai'],
        '法规覆盖情况': ['完全覆盖', '部分覆盖', '完全覆盖'],
        '条款编号': ['第五条', '第二十四条', '第四条'],
        '适用对象': ['中央企业'] * 3,
        '强制等级': ['强制'] * 3,
        '实施要求': [
            '要求中央企业按照本办法建立从立项、决策、执行到监督的全流程管理体系，确保决策程序透明、责任落实和监管备案到位。',
            '中央企业应当将境外投资风险管理作为投资风险管理体系的重要内容。',
            '国资委指导中央企业建立健全境外投资管理制度，强化战略规划引领。'
        ],
        '要求建立的制度': [
            '境外投资管理制度；境外投资项目负面清单制度',
            '境外投资前期风险评估制度',
            '境外投资管理制度'
        ],
        '要求建立的管理体系': [
            '中央企业境外投资监督管理体系',
            '项目实施过程中的风险监控体系',
            '境外投资监督管理体系'
        ],
        '负面清单': [
            '依据负面清单对境外投资项目进行分类监管',
            '',
            '制定中央企业境外投资项目负面清单'
        ],
        '要求提交的报告': ['', '', '监督检查报告'],
        '要求提供的信息和数据': ['', '', '通过信息系统报送电子版信息']
    }
    
    # Create DataFrame and save as Excel for testing
    df = pd.DataFrame(sample_data)
    test_file = 'test_regulation_data.xlsx'
    df.to_excel(test_file, index=False)
    
    print("Created test Excel file:", test_file)
    return test_file

# Main execution
if __name__ == "__main__":
    # For testing - create sample data
    # test_file = test_conversion()
    
    # Use your actual Excel file
    excel_file = "企业境外投资管理办法-1.xlsx"  # Replace with your actual file path
    output_json = "企业境外投资管理办法.json"
    
    # Convert Excel to JSON
    print("Starting conversion...")
    result = convert_excel_to_json(excel_file, output_json)
    
    if result:
        print("\n=== Conversion completed successfully! ===")
        print(f"Output saved to: {output_json}")
        
        # Display summary
        for provider, data in result["LLM分析结果"].items():
            if isinstance(data, dict) and "详细分析" in data:
                total_categories = len(data["详细分析"])
                total_requirements = sum(len(reqs) for reqs in data["详细分析"].values())
                print(f"\nProvider: {provider}")
                print(f"  Categories: {total_categories}")
                print(f"  Total Requirements: {total_requirements}")
                print(f"  Key Findings: {len(data.get('关键发现', []))}")
                print(f"  Recommendations: {len(data.get('合规建议', []))}")
    else:
        print("Conversion failed!")

# Utility function to preview Excel structure
def preview_excel_structure(excel_file):
    """
    Preview the Excel file structure
    
    Args:
        excel_file (str): Path to Excel file
    """
    try:
        df = pd.read_excel(excel_file)
        print("=== Excel File Structure ===")
        print(f"Total rows: {len(df)}")
        print(f"Total columns: {len(df.columns)}")
        print("\nColumns:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i}. {col}")
        
        print("\nFirst few rows:")
        print(df.head(3).to_string())
        
        if '分析专家' in df.columns:
            print(f"\nAnalysts found: {df['分析专家'].unique()}")
        
        if '大类要素名称' in df.columns:
            print(f"\nCategories found: {df['大类要素名称'].unique()}")
            
        return df
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None