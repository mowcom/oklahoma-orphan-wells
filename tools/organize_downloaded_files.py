#!/usr/bin/env python3
"""Organize manually downloaded files into proper landman structure"""

import shutil
from pathlib import Path
import os

def organize_manual_downloads():
    """Organize manually downloaded files into landman categories"""
    
    print("📁 ORGANIZING MANUALLY DOWNLOADED FILES")
    print("=" * 50)
    
    # Paths
    well_folder = Path("output/API_35_009_21739_0000")
    downloads_folder = well_folder / "files_downloaded"
    
    # Create category folders
    categories = {
        'PERMITS': 'permits',
        'COMPLETION_REPORTS': 'completion_reports', 
        'PRODUCTION_DATA': 'production_data',
        'STATUS_CHANGES': 'status_changes',
        'CORRESPONDENCE': 'correspondence',
        'OTHER': 'other'
    }
    
    for category in categories.keys():
        (downloads_folder / category).mkdir(parents=True, exist_ok=True)
    
    print("✅ Created category folders")
    
    # File categorization rules based on your screenshot
    file_categories = {
        # Forms 1000 - Permits
        'Form 1000': 'PERMITS',
        'form_1000': 'PERMITS',
        '1000': 'PERMITS',
        
        # Forms 1001A - Applications  
        'Form 1001A': 'PERMITS',
        'form_1001a': 'PERMITS',
        '1001a': 'PERMITS',
        
        # Forms 1002A/C - Completion
        'Form 1002A': 'COMPLETION_REPORTS',
        'Form 1002C': 'COMPLETION_REPORTS', 
        'form_1002a': 'COMPLETION_REPORTS',
        'form_1002c': 'COMPLETION_REPORTS',
        '1002a': 'COMPLETION_REPORTS',
        '1002c': 'COMPLETION_REPORTS',
        
        # Form 1016 - Production
        'Form 1016': 'PRODUCTION_DATA',
        'form_1016': 'PRODUCTION_DATA',
        '1016': 'PRODUCTION_DATA',
        
        # Form 1073 - Status Changes
        'Form 1073': 'STATUS_CHANGES',
        'form_1073': 'STATUS_CHANGES', 
        '1073': 'STATUS_CHANGES',
    }
    
    print("\n📋 EXPECTED FILES (from your screenshot):")
    expected_files = [
        "Form 1000 - 03-13-2008.pdf",
        "Form 1000 - 10-24-2008.pdf", 
        "Form 1001A - 03-29-2008.pdf",
        "Form 1002A - 10-01-2008.pdf",
        "Form 1002C - 04-14-2008.pdf",
        "Form 1016 - 10-02-2008.pdf",
        "Form 1073 - 02-28-2011.pdf"
    ]
    
    for expected in expected_files:
        print(f"   📄 {expected}")
    
    print(f"\n🔍 Looking for downloaded files in common locations:")
    
    # Common download locations to check
    search_paths = [
        Path.home() / "Downloads",
        Path.home() / "Desktop", 
        Path.cwd() / "downloads",
        Path.cwd(),
        well_folder,
    ]
    
    found_files = []
    
    for search_path in search_paths:
        if search_path.exists():
            print(f"\n   📂 Checking: {search_path}")
            
            # Look for PDF files that might be our documents
            pdf_files = list(search_path.glob("*.pdf"))
            relevant_files = []
            
            for pdf_file in pdf_files:
                file_name = pdf_file.name.lower()
                # Check if filename contains form numbers
                if any(form_id in file_name for form_id in ['1000', '1001', '1002', '1016', '1073']):
                    relevant_files.append(pdf_file)
                    print(f"     ✅ Found: {pdf_file.name}")
            
            found_files.extend(relevant_files)
    
    if found_files:
        print(f"\n📥 ORGANIZING {len(found_files)} FILES:")
        
        for file_path in found_files:
            file_name = file_path.name.lower()
            
            # Determine category
            target_category = 'OTHER'
            for form_id, category in file_categories.items():
                if form_id.lower() in file_name:
                    target_category = category
                    break
            
            # Copy file to appropriate category
            target_dir = downloads_folder / target_category
            target_path = target_dir / file_path.name
            
            try:
                shutil.copy2(file_path, target_path)
                print(f"   📄 {file_path.name} → {target_category}/")
            except Exception as e:
                print(f"   ❌ Error copying {file_path.name}: {e}")
    
    else:
        print(f"\n📍 NO FILES FOUND AUTOMATICALLY")
        print(f"   Please manually place downloaded files in:")
        print(f"   {downloads_folder}")
        print(f"\n   Then run this script again, or organize manually:")
        
        for category, description in {
            'PERMITS': 'Form 1000, 1001A files',
            'COMPLETION_REPORTS': 'Form 1002A, 1002C files', 
            'PRODUCTION_DATA': 'Form 1016 files',
            'STATUS_CHANGES': 'Form 1073 files'
        }.items():
            print(f"   📂 {category}/ - {description}")
    
    # Show final structure
    print(f"\n📁 FINAL STRUCTURE:")
    for category in categories.keys():
        category_dir = downloads_folder / category
        files_in_category = list(category_dir.glob("*"))
        print(f"   📂 {category}/ ({len(files_in_category)} files)")
        for file_path in files_in_category:
            print(f"     📄 {file_path.name}")

if __name__ == "__main__":
    organize_manual_downloads()