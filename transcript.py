import json
import re
import sys
import pypandoc

# Constants
INSTRUCTIONS_TITLE = "Instructions"
INSTRUCTIONS_PROSE = ""
WALKTHROUGH_TITLE = "Walkthrough"
WALKTHROUGH_PROSE = ""
TRANSCRIPT_TITLE = "Transcript"
TRANSCRIPT_PROSE = ""
PARSKIP="6pt plus 2pt"

def escape_latex(text):
    """Escape special LaTeX characters."""
    text = text.replace('\\', '\\textbackslash{}')
    text = text.replace('_', '\\_')
    text = text.replace('#', '\\#')
    text = text.replace('$', '\\$')
    text = text.replace('%', '\\%')
    text = text.replace('&', '\\&')
    text = text.replace('{', '\\{')
    text = text.replace('}', '\\}')
    text = text.replace('~', '\\textasciitilde{}')
    text = text.replace('^', '\\textasciicircum{}')
    text = text.replace('---------', '\\rule[0.275em]{6em}{0.6pt}')
    return text

def convert_markdown_to_latex(md_text):
    """Convert Markdown to LaTeX, mapping # to \\subsubsection*."""
    latex = pypandoc.convert_text(md_text, 'latex', format='md', extra_args=['--shift-heading-level-by=2'])
    latex = re.sub(r'\\subsubsection\{', r'\\subsubsection*{', latex)
    return latex

def process_user_content(content, is_first=False):
    """Process user message content for LaTeX rendering."""
    # Handle special case for first message if needed
    if is_first:
        match = re.search(r'You are hungry!', content)
        if match:
            content = content[match.start():]
    
    # Step 1: Escape the entire content first
    content = escape_latex(content)
    
    # Step 2: Substitute room titles with LaTeX command
    content = re.sub(r'-=\s*(.*?)\s*=-', r'\\roomtitle{\1}', content)
    
    # Remove trailing prompt if present
    content = re.sub(r'\s*>\s*$', '', content)

    content = re.sub(r'"looking\."', "``looking.''", content)
    content = re.sub(r'"Cooking', '``Cooking', content)
    content = re.sub(r'\)"', ")''", content)
    
    
    # Split into lines and group into paragraphs
    lines = content.split('\n')
    paragraphs = []
    current_paragraph = []
    for line in lines:
        if line.strip() == '':
            if current_paragraph:
                paragraphs.append(current_paragraph)
                current_paragraph = []
        else:
            current_paragraph.append(line)
    if current_paragraph:
        paragraphs.append(current_paragraph)
    
    # Process each paragraph
    latex_paragraphs = []
    for para in paragraphs:
        if len(para) > 1 and para[0].strip() in ["Ingredients:", "Directions:"]:
            # Handle lists (e.g., Ingredients or Directions)
            list_type = para[0].strip()  # Already escaped
            items = [line.strip() for line in para[1:] if line.strip()]
            latex_list = [f"\\item[] {item}" for item in items]  # Items are already escaped
            latex_paragraphs.append(
                f"{list_type}\n\\begin{{itemize}}[topsep=-\\parsep]\n\\tightlist\n" + 
                '\n'.join(latex_list) + 
                "\n\\end{itemize}"
            )
        else:
            # Single-line or multi-line non-list paragraph
            text = ' '.join(para)  # Already escaped and may contain \roomtitle{...}
            latex_paragraphs.append(text)
    
    # Join paragraphs with double newlines
    return '\n\n'.join(latex_paragraphs)

def parse_assistant_content(content):
    """Parse assistant content into thoughts and command."""
    match = re.match(r'((\(.*\)\s*)+)(.*)', content)
    if match:
        return match.group(1), match.group(3)
    else:
        return "", content

def render_messages(messages, is_walkthrough=True):
    """Render messages into a LaTeX fragment."""
    latex = []
    first_user = True
    i = 0
    while i < len(messages):
        if messages[i]['role'] == 'user':
            user_content = process_user_content(messages[i]['content'], is_first=first_user)
            latex.append(user_content)
            first_user = False
            i += 1
            if i < len(messages) and messages[i]['role'] == 'assistant':
                thoughts, command = parse_assistant_content(messages[i]['content'])
                latex.append(f"\\playerinput{{{escape_latex(thoughts)}}}{{{escape_latex(command)}}}")
                i += 1
            while not is_walkthrough and i < len(messages) and messages[i]['role'] == 'developer':
                developer_content = messages[i]['content']
                latex.append(f"\\errormessage{{{escape_latex(developer_content)}}}")
                i += 1
            latex.append("")  # Paragraph break
        else:
            i += 1
    return '\n\n'.join(latex)

def main(data):
    """Generate LaTeX fragment from JSON data."""
    messages = data['messages']
    developer_indices = [i for i, msg in enumerate(messages) if msg['role'] == 'developer']
    if len(developer_indices) < 2:
        raise ValueError("Input JSON must contain at least two developer messages.")
    instructions_md = messages[developer_indices[0]]['content']
    instructions_latex = convert_markdown_to_latex(instructions_md)
    walkthrough_messages = messages[developer_indices[0] + 1:developer_indices[1]]
    walkthrough_latex = render_messages(walkthrough_messages, is_walkthrough=True)
    transcript_messages = messages[developer_indices[1] + 1:]
    transcript_latex = render_messages(transcript_messages, is_walkthrough=False)
    latex = []
    latex.append(f"\\subsection*{{{INSTRUCTIONS_TITLE}}}\n{INSTRUCTIONS_PROSE}\n\n{instructions_latex}")
    latex.append(f"\\subsection*{{{WALKTHROUGH_TITLE}}}\n\\begingroup\n\\setlength{{\\parindent}}{{0pt}}\n\\setlength{{\\parskip}}{{{PARSKIP}}}\n{WALKTHROUGH_PROSE}\n\n{walkthrough_latex}\n\\endgroup\\newpage")
    latex.append(f"\\subsection*{{{TRANSCRIPT_TITLE}}}\n\\begingroup\n\\setlength{{\\parindent}}{{0pt}}\n\\setlength{{\\parskip}}{{{PARSKIP}}}\n{TRANSCRIPT_PROSE}\n\n{transcript_latex}\n\\endgroup")
    return '\n\n'.join(latex)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)
    latex_output = main(data)
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w') as f:
            f.write(latex_output)
    else:
        print(latex_output)