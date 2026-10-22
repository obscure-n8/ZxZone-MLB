import os
import zipfile
import subprocess

def make_zip(source_folder, output_zip_path):
    """যেকোনো ফোল্ডার বা ফাইলকে .zip আর্কাইভে রূপান্তর করা"""
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_folder):
            for file in files:
                full_path = os.path.join(root, file)
                zipf.write(full_path, os.path.relpath(full_path, source_folder))
    return output_zip_path

def extract_archive(archive_path, extract_dir):
    """জিপ বা অন্য কোনো আর্কাইভ ফাইল এক্সট্রাক্ট (Unzip) করা"""
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    return extract_dir

def split_large_file(file_path, chunk_size_mb=2000):
    """বড় ফাইলকে নিমিষেই টেলিগ্রাম ফ্রেন্ডলি পার্টে স্প্লিট করা"""
    dir_name = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)
    cmd = ["split", "-b", f"{chunk_size_mb}M", file_path, os.path.join(dir_name, f"{base_name}.part")]
    subprocess.run(cmd)
    return [os.path.join(dir_name, f) for f in os.listdir(dir_name) if f.startswith(f"{base_name}.part")]
