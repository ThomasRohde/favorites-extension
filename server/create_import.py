import re
import json
from urllib.parse import urlparse

def parse_markdown(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Regular expression to match Markdown links with descriptions
    pattern = r'^- \[(.*?)\]\((https?://\S+)\)\s*:?\s*(.*?)$'
    
    # Regular expression to match headers
    header_pattern = r'^#+\s+(.*?)$'

    current_header = ""
    links = []

    for line in content.split('\n'):
        header_match = re.match(header_pattern, line)
        if header_match:
            current_header = header_match.group(1).strip()
        else:
            match = re.match(pattern, line)
            if match:
                title, url, description = match.groups()
                links.append({
                    "url": url,
                    "title": title,
                    "metadata": f"Header: {current_header}\nDescription: {description.strip()}"
                })

    return links

def create_json_for_import(links):
    return json.dumps(links, indent=2)

def main():
    markdown_file = "generative_ai_links.md"  # Replace with your Markdown file path
    output_file = "import_ready_links.json"

    links = parse_markdown(markdown_file)
    json_output = create_json_for_import(links)

    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(json_output)

    print(f"JSON file '{output_file}' has been created successfully.")

if __name__ == "__main__":
    main()