#!/usr/bin/env python3
"""
Script to render a Mermaid diagram as an image.
This script takes a Mermaid diagram code from a markdown file and renders it as a PNG image.
"""

import os
import re
import sys
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def render_mermaid(mermaid_code, output_path):
    """
    Render a Mermaid diagram as a PNG image using Playwright.
    
    Args:
        mermaid_code (str): The Mermaid diagram code
        output_path (str): Path where to save the generated PNG image
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Create a simple HTML page with Mermaid
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            <script>
                mermaid.initialize({{
                    startOnLoad: true,
                    theme: 'default',
                    flowchart: {{ useMaxWidth: false }}
                }});
            </script>
            <style>
                body {{
                    background: white;
                    display: flex;
                    justify-content: center;
                    padding: 20px;
                }}
                .diagram {{
                    max-width: 100%;
                }}
            </style>
        </head>
        <body>
            <div class="diagram">
                <div class="mermaid">
                {mermaid_code}
                </div>
            </div>
        </body>
        </html>
        """
        
        await page.set_content(html_content)
        
        # Wait for Mermaid to render
        await page.wait_for_selector(".mermaid svg")
        
        # Get the dimensions of the SVG
        dimensions = await page.evaluate("""
            () => {
                const svg = document.querySelector('.mermaid svg');
                return {
                    width: svg.width.baseVal.value,
                    height: svg.height.baseVal.value
                };
            }
        """)
        
        # Set viewport to match SVG size
        await page.set_viewport_size({
            "width": int(dimensions["width"]) + 40,  # Add padding
            "height": int(dimensions["height"]) + 40  # Add padding
        })
        
        # Take a screenshot of just the Mermaid diagram
        diagram = await page.query_selector(".mermaid")
        await diagram.screenshot(path=output_path)
        
        await browser.close()
        
        print(f"Mermaid diagram rendered successfully to {output_path}")

def extract_mermaid_from_markdown(markdown_path):
    """
    Extract a Mermaid diagram code from a markdown file.
    
    Args:
        markdown_path (str): Path to the markdown file
        
    Returns:
        str: The extracted Mermaid diagram code
    """
    with open(markdown_path, 'r') as f:
        content = f.read()
    
    # Find Mermaid code block
    mermaid_match = re.search(r'```mermaid\n(.*?)```', content, re.DOTALL)
    if not mermaid_match:
        raise ValueError("No Mermaid diagram found in the markdown file")
    
    return mermaid_match.group(1)

def update_markdown_with_image(markdown_path, image_path, mermaid_code):
    """
    Update the markdown file to include the generated image.
    
    Args:
        markdown_path (str): Path to the markdown file
        image_path (str): Path to the image file
        mermaid_code (str): Original Mermaid diagram code
    """
    with open(markdown_path, 'r') as f:
        content = f.read()
    
    # Replace the Mermaid code block with both the image and the original code (commented out)
    image_ref = f'![Architecture Diagram]({os.path.basename(image_path)})\n\n<!-- Original Mermaid diagram code:\n```mermaid\n{mermaid_code}```\n-->'
    updated_content = re.sub(r'```mermaid\n.*?```', image_ref, content, flags=re.DOTALL)
    
    with open(markdown_path, 'w') as f:
        f.write(updated_content)
    
    print(f"Markdown file {markdown_path} updated with image reference")

async def main():
    markdown_file = 'architecture_plans.md'
    output_image = 'architecture_mermaid.png'
    
    try:
        # Extract Mermaid code from markdown
        mermaid_code = extract_mermaid_from_markdown(markdown_file)
        
        # Render the Mermaid diagram
        await render_mermaid(mermaid_code, output_image)
        
        # Update the markdown file
        update_markdown_with_image(markdown_file, output_image, mermaid_code)
        
        print("Process completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
