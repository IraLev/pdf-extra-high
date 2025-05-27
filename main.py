"""
PDF Highlight Extractor
======================

A robust tool for extracting highlighted text from PDF files with intelligent text ordering
and hyphenation handling.

Overview:
--------
This tool addresses common PDF text extraction challenges:
- PDFs store text in creation order, not reading order
- Multi-line highlights can extract in wrong sequence
- Hyphenated words across lines need rejoining
- Boundary words may be partially highlighted

Architecture:
------------
1. PDFHighlightExtractor: Main class handling extraction logic
2. Multi-method extraction: Fallback system for maximum compatibility
3. Smart text ordering: Line detection and geometric sorting
4. Hyphenation merger: Detects and combines split words

Technical Approach:
-----------------
METHOD A: PyMuPDF built-in text sorting
- Uses page.get_text("text", sort=True) for automatic ordering
- Most reliable for simple layouts

METHOD B: Text block extraction
- Extracts PDF text blocks which maintain better reading order
- Geometric sorting by block position

METHOD C: Enhanced word-level sorting
- Individual word extraction with custom line detection
- Groups words by Y-position, sorts by X-position within lines
- Handles complex multi-line highlights

Hyphenation Algorithm:
--------------------
1. Detects highlights ending with '-'
2. Checks next highlight for same color and reasonable distance
3. Merges: "lin-" + "guistics" → "linguistics"
4. Supports both same-page and cross-page hyphenation

Color Detection:
---------------
- RGB color space analysis
- Supports 4 highlight colors: Yellow, Pink, Green, Blue
- Handles both fill and stroke color properties

Precision Control:
-----------------
- 40% overlap threshold for word inclusion
- +2 pixel boundary expansion for edge cases
- 5-pixel line tolerance for multi-line detection

Usage Patterns:
--------------
Test Mode: python script.py --test
- Uses default PDF path
- Display-only output
- Quick testing and debugging

Full Mode: python script.py
- Interactive prompts for file paths
- Optional JSON/CSV export
- Complete control over options
"""
import time
import pdfplumber
import fitz  # PyMuPDF
import json
from colorama import init, Fore, Back, Style
import pandas as pd
from pathlib import Path
import re
import sys

# Initialize colorama for colored terminal output
init(autoreset=True)

class PDFHighlightExtractor:
    """
Main extraction class for PDF highlighted text.

This class handles the complete extraction pipeline from PDF analysis
to formatted output with intelligent text ordering and hyphenation.

Key Features:
------------
- Multi-method text extraction with fallback
- Geometric text ordering for proper reading sequence
- Hyphenation detection and merging
- 4-color highlight support (Yellow, Pink, Green, Blue)
- Cross-page highlight handling

Extraction Pipeline:
------------------
1. PDF Loading: Opens PDF with PyMuPDF
2. Annotation Detection: Finds highlight annotations
3. Color Classification: Identifies highlight colors
4. Text Extraction: Uses multi-method approach
5. Text Ordering: Applies geometric sorting
6. Hyphenation Merging: Combines split words
7. Output Formatting: Prepares results for display/export

Methods Overview:
---------------
extract_all_highlights(): Main entry point
_extract_text_balanced(): Core text extraction with ordering
_smart_hyphenation_merge(): Hyphenation detection and merging
_is_clear_hyphenation(): Hyphenation pattern recognition
display_results(): Formatted terminal output

Usage:
------
extractor = PDFHighlightExtractor('path/to/file.pdf')
annotations, highlights = extractor.extract_all_highlights()
extractor.display_results()
"""
def __init__(self, pdf_path):
    self.pdf_path = Path(pdf_path)
    self.annotations = []
    self.highlights = []

def extract_annotation_highlights(self):
    """Extract annotations with simple processing."""
    annotations = []
    try:
        with pdfplumber.open(self.pdf_path) as pdf:
            print(f"📄 Processing annotations...")
            for page_num, page in enumerate(pdf.pages, 1):
                if hasattr(page, 'annots') and page.annots:
                    for annot in page.annots:
                        try:
                            annot_type = annot.get('subtype', 'Unknown')
                            if annot_type in ['Highlight', 'Squiggly', 'StrikeOut', 'Underline', 'FreeText', 'Text']:
                                rect = annot.get('rect', [])
                                text = self._get_annotation_text(page, annot, rect)
                                color = self._get_simple_color(annot.get('color', []))
                                
                                if text and text.strip():
                                    annotations.append({
                                        'page': page_num,
                                        'text': text.strip(),
                                        'color': color,
                                        'type': 'annotation',
                                        'y_position': rect[1] if len(rect) >= 4 else 0
                                    })
                        except:
                            continue
        
        print(f"  ✅ Found {len(annotations)} annotations")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return annotations

def extract_background_highlights(self):
    """Extract highlights with BALANCED precision - capture complete highlights."""
    all_highlights = []
    
    try:
        print(f"\n🎨 Processing highlights...")
        doc = fitz.open(str(self.pdf_path))
        
        # Collect each individual highlight with BALANCED extraction
        for page_num in range(doc.page_count):
            page = doc[page_num]
            annotations = page.annots()
            
            for annot in annotations:
                try:
                    if annot.type[1] == 'Highlight':
                        colors = annot.colors
                        color_name = self._get_highlight_color(colors)
                        
                        if color_name in ['yellow', 'pink', 'green', 'blue']:
                            # BALANCED: Extract complete highlighted phrases
                            text = self._extract_text_balanced(page, annot)
                            
                            if text and text.strip():
                                all_highlights.append({
                                    'page': page_num + 1,
                                    'text': text.strip(),
                                    'color': color_name,
                                    'type': 'highlight',
                                    'y_position': annot.rect.y0,
                                    'x_position': annot.rect.x0,
                                    'y_end': annot.rect.y1,
                                    'x_end': annot.rect.x1,
                                    'rect': annot.rect
                                })
                                print(f"    🎨 {color_name.upper()}: \"{text[:70]}...\"")
                except Exception as e:
                    continue
        
        doc.close()
        
        # Smart hyphenation merging only
        merged_highlights = self._smart_hyphenation_merge(all_highlights)
        
        print(f"  📊 Raw: {len(all_highlights)} → Merged: {len(merged_highlights)}")
        return merged_highlights
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def _extract_text_balanced(self, page, annot):
    """BALANCED: Extract text with PROPER READING ORDER."""
    try:
        # Method 1: Use PyMuPDF's built-in text ordering with sorting
        highlight_rect = annot.rect
        
        # SMALL EXPANSION for boundary words
        expanded_rect = fitz.Rect(
            highlight_rect.x0 - 2,
            highlight_rect.y0 - 1, 
            highlight_rect.x1 + 2,
            highlight_rect.y1 + 1
        )
        
        # METHOD A: Use text extraction with BUILT-IN SORTING
        print(f"      🔍 Method A: Text extraction with sorting")
        text_with_sort = page.get_text("text", clip=expanded_rect, sort=True)
        if text_with_sort and text_with_sort.strip():
            cleaned_text = re.sub(r'\s+', ' ', text_with_sort.strip())
            print(f"      ✅ Sorted text result: \"{cleaned_text}\"")
            return cleaned_text
        
        # METHOD B: Text blocks (better reading order than individual words)
        print(f"      🔍 Method B: Text blocks extraction")
        text_blocks = page.get_text("blocks", clip=expanded_rect)
        if text_blocks:
            # Sort blocks by reading order (top to bottom, left to right)
            text_blocks.sort(key=lambda block: (block[1], block[0]))  # y-pos, then x-pos
            
            block_texts = []
            for block in text_blocks:
                if len(block) >= 5 and block[4].strip():
                    block_text = block[4].strip()
                    block_text = re.sub(r'\s+', ' ', block_text)
                    block_texts.append(block_text)
            
            if block_texts:
                combined_text = " ".join(block_texts)
                print(f"      ✅ Block result: \"{combined_text}\"")
                return combined_text
        
        # METHOD C: Enhanced word-level with geometric sorting
        print(f"      🔍 Method C: Enhanced word sorting")
        all_words = page.get_text("words")
        highlight_words = []
        
        for word in all_words:
            word_rect = fitz.Rect(word[:4])
            word_text = word[4]
            
            if expanded_rect.intersects(word_rect):
                intersection = expanded_rect & word_rect
                word_area = word_rect.get_area()
                
                if word_area > 0:
                    overlap_ratio = intersection.get_area() / word_area
                    
                    if overlap_ratio >= 0.40:
                        highlight_words.append({
                            'text': word_text,
                            'x0': word[0],
                            'y0': word[1],
                            'x1': word[2],
                            'y1': word[3],
                            'center_y': (word[1] + word[3]) / 2,
                            'center_x': (word[0] + word[2]) / 2
                        })
        
        if highlight_words:
            # ENHANCED SORTING: Group by lines first, then sort within lines
            # Group words by approximate line (within 5 pixels of each other)
            lines = []
            for word in highlight_words:
                placed = False
                for line in lines:
                    # Check if word belongs to existing line
                    avg_y = sum(w['center_y'] for w in line) / len(line)
                    if abs(word['center_y'] - avg_y) <= 5:  # Same line tolerance
                        line.append(word)
                        placed = True
                        break
                
                if not placed:
                    lines.append([word])
            
            # Sort lines by Y position (top to bottom)
            lines.sort(key=lambda line: sum(w['center_y'] for w in line) / len(line))
            
            # Sort words within each line by X position (left to right)
            for line in lines:
                line.sort(key=lambda w: w['center_x'])
            
            # Combine all words in reading order
            ordered_words = []
            for line in lines:
                ordered_words.extend(line)
            
            extracted_text = " ".join([w['text'] for w in ordered_words])
            print(f"      ✅ Enhanced word sorting ({len(ordered_words)} words): \"{extracted_text}\"")
            return extracted_text
        
        print(f"      ❌ No text found in highlight area")
        return ""
        
    except Exception as e:
        print(f"      ❌ Extraction error: {e}")
        return ""


def _extract_by_quads_balanced(self, page, annot):
    """Extract using quad points with BALANCED precision."""
    try:
        quad_points = annot.vertices
        if not quad_points:
            return ""
            
        quad_count = int(len(quad_points) / 4)
        all_words = page.get_text("words")
        highlight_words = []
        
        print(f"      🔍 Processing {quad_count} quads with balanced precision")
        
        for i in range(quad_count):
            points = quad_points[i * 4: i * 4 + 4]
            quad_rect = fitz.Quad(points).rect
            
            # SMALL EXPANSION - 2 pixels to catch boundary words
            expanded_quad = fitz.Rect(
                quad_rect.x0 - 2, quad_rect.y0 - 1,
                quad_rect.x1 + 2, quad_rect.y1 + 1
            )
            
            for word in all_words:
                word_rect = fitz.Rect(word[:4])
                word_text = word[4]
                
                if expanded_quad.intersects(word_rect):
                    intersection = expanded_quad & word_rect
                    word_area = word_rect.get_area()
                    
                    if word_area > 0:
                        overlap_ratio = intersection.get_area() / word_area
                        
                        # RELAXED: 40% overlap required (was 75%)
                        if overlap_ratio >= 0.40:
                            highlight_words.append({
                                'text': word_text,
                                'x0': word[0],
                                'y0': word[1],
                                'line': self._estimate_line_number(word[1])
                            })
                            print(f"        ✓ Quad '{word_text}' (overlap: {overlap_ratio:.2f})")
        
        if highlight_words:
            # Remove duplicates while preserving order
            seen = set()
            unique_words = []
            for word in highlight_words:
                word_key = (word['text'], word['x0'], word['y0'])
                if word_key not in seen:
                    seen.add(word_key)
                    unique_words.append(word)
            
            # Sort by reading order
            unique_words.sort(key=lambda w: (w['line'], w['x0']))
            extracted_text = " ".join([w['text'] for w in unique_words])
            print(f"      ✅ Quad balanced ({len(unique_words)} words): \"{extracted_text}\"")
            return extracted_text
        
        return ""
        
    except Exception as e:
        print(f"      ❌ Quad extraction error: {e}")
        return ""

def _estimate_line_number(self, y_position, avg_line_height=14):
    """Estimate line number based on y-position."""
    return round(y_position / avg_line_height)

def _smart_hyphenation_merge(self, highlights):
    """Smart merging - ONLY for clear hyphenation patterns."""
    if not highlights:
        return highlights
    
    # Sort by page, color, then position
    highlights.sort(key=lambda x: (x['page'], x['color'], x['y_position'], x['x_position']))
    
    merged = []
    i = 0
    
    while i < len(highlights):
        current = highlights[i]
        
        # Look for hyphenation continuation
        if (i + 1 < len(highlights) and 
            self._is_clear_hyphenation(current, highlights[i + 1])):
            
            next_hl = highlights[i + 1]
            merged_text = self._join_hyphenated_text(current['text'], next_hl['text'])
            
            merged_highlight = current.copy()
            merged_highlight['text'] = merged_text
            
            if current['page'] != next_hl['page']:
                merged_highlight['pages_spanned'] = f"Pages {current['page']}-{next_hl['page']}"
                print(f"  🔗 Cross-page hyphen: \"{merged_text[:80]}\"")
            else:
                merged_highlight['hyphen_merged'] = True
                print(f"  🔗 Same-page hyphen: \"{merged_text[:80]}\"")
                
            merged.append(merged_highlight)
            i += 2  # Skip both highlights
        else:
            merged.append(current)
            i += 1
    
    return merged

def _is_clear_hyphenation(self, hl1, hl2):
    """Detect ONLY clear hyphenation patterns."""
    # Must be same color
    if hl1['color'] != hl2['color']:
        return False
    
    text1 = hl1['text'].strip()
    text2 = hl2['text'].strip()
    
    # MUST end with hyphen for hyphenation
    if not text1.endswith('-'):
        return False
    
    # Same page: check reasonable line spacing
    if hl1['page'] == hl2['page']:
        y_diff = abs(hl1['y_position'] - hl2['y_position'])
        # Reasonable line height (8-30 pixels) - slightly more lenient
        if 8 <= y_diff <= 30 and hl2['y_position'] > hl1['y_position']:
            print(f"  🔍 Same-page hyphen detected: '{text1}' + '{text2[:15]}'")
            return True
    
    # Cross-page: second highlight should be near top
    elif hl2['page'] == hl1['page'] + 1 and hl2['y_position'] < 150:
        print(f"  🔍 Cross-page hyphen detected: '{text1}' + '{text2[:15]}'")
        return True
    
    return False

def _join_hyphenated_text(self, text1, text2):
    """Join hyphenated text correctly."""
    text1 = text1.strip()
    text2 = text2.strip()
    
    if text1.endswith('-'):
        # Remove hyphen and join
        return text1[:-1] + text2
    else:
        return text1 + " " + text2

def _get_highlight_color(self, colors):
    """Get highlight color - only 4 colors."""
    if not colors:
        return 'unknown'
    
    if 'fill' in colors and colors['fill']:
        rgb = colors['fill']
    elif 'stroke' in colors and colors['stroke']:
        rgb = colors['stroke']
    else:
        return 'unknown'
    
    return self._rgb_to_simple_color(rgb)
def _rgb_to_simple_color(self, rgb):
    """Convert RGB to one of 4 colors."""
    if not rgb or len(rgb) < 3:
        return 'unknown'
    
    r, g, b = rgb[:3]
    
    if r <= 1:
        r, g, b = r*255, g*255, b*255
    
    if r > 220 and g > 220 and b < 120:
        return 'yellow'
    elif r < 120 and g > 180 and b < 120:
        return 'green'
    elif r < 120 and g < 180 and b > 180:
        return 'blue'
    elif r > 180 and g < 180 and b > 180:
        return 'pink'
    else:
        max_val = max(r, g, b)
        if max_val == r and r > 150:
            return 'pink'
        elif max_val == g and g > 150:
            return 'green'
        elif max_val == b and b > 150:
            return 'blue'
        elif r > 180 and g > 180:
            return 'yellow'
        return 'unknown'

def _get_simple_color(self, color_rgb):
    """Get simple color from annotation."""
    if color_rgb:
        return self._rgb_to_simple_color(color_rgb)
    return 'unknown'

def _get_annotation_text(self, page, annot, rect):
    """Extract annotation text."""
    text = annot.get('contents', '').strip()
    if text:
        return text
    
    if rect and len(rect) == 4:
        try:
            x0, y0, x1, y1 = rect
            cropped = page.crop((x0-1, y0-1, x1+1, y1+1))
            text = cropped.extract_text()
            if text and text.strip():
                return text.strip()
        except:
            pass
    
    return ""

def extract_all_highlights(self):
    """Main extraction method."""
    print("🔍 PDF Highlight Extractor - BALANCED PRECISION")
    print("🎯 Colors: Yellow, Pink, Green, Blue only")
    print("🎯 BALANCED extraction - complete highlights without over-capture")
    print("📏 Small expansion (+2 pixels) for boundary words")
    print("🔍 40% overlap requirement (was 75% - more inclusive)")
    print("🔗 Smart hyphenation merging")
    print("=" * 70)
    
    self.annotations = self.extract_annotation_highlights()
    self.highlights = self.extract_background_highlights()
    
    print(f"\n✨ Total: {len(self.annotations)} annotations, {len(self.highlights)} highlights")
    return self.annotations, self.highlights

def display_results(self):
    """Display results cleanly."""
    print("\n" + "="*70)
    print("📋 EXTRACTION RESULTS")
    print("="*70)
    
    all_items = []
    for item in self.annotations:
        item['category'] = 'annotation'
        all_items.append(item)
    for item in self.highlights:
        item['category'] = 'highlight'
        all_items.append(item)
    
    if not all_items:
        print("\n❌ No highlights found")
        return
    
    all_items.sort(key=lambda x: (x['page'], x['y_position']))
    
    current_page = None
    for item in all_items:
        if item['page'] != current_page:
            current_page = item['page']
            print(f"\n📄 Page {current_page}")
            print("-" * 25)
        
        color_code = self._get_color_display(item['color'])
        icon = "📝" if item['category'] == 'annotation' else "🎨"
        
        merge_info = ""
        if item.get('pages_spanned'):
            merge_info = f" ({item['pages_spanned']})"
        elif item.get('hyphen_merged'):
            merge_info = " (hyphen-merged)"
        
        print(f"{icon} {color_code}{item['color'].upper()}{Style.RESET_ALL}{merge_info}")
        print(f"   \"{item['text']}\"")

def _get_color_display(self, color_name):
    """Terminal color codes."""
    colors = {
        'yellow': Back.YELLOW + Fore.BLACK,
        'green': Back.GREEN + Fore.BLACK,
        'blue': Back.BLUE + Fore.WHITE,
        'pink': Back.MAGENTA + Fore.WHITE,
    }
    return colors.get(color_name, Back.WHITE + Fore.BLACK)

def save_to_json(self, annotations, highlights, output_path):
    """Save to JSON."""
    data = {
        'annotations': annotations,
        'highlights': highlights,
        'summary': {
            'total_annotations': len(annotations),
            'total_highlights': len(highlights)
        }
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved to {output_path}")

def save_to_csv(self, annotations, highlights, output_path):
    """Save to CSV."""
    all_items = []
    for item in annotations:
        item_copy = item.copy()
        item_copy['category'] = 'annotation'
        all_items.append(item_copy)
    for item in highlights:
        item_copy = item.copy()
        item_copy['category'] = 'highlight'
        all_items.append(item_copy)
    
    df = pd.DataFrame(all_items)
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"📊 Saved to {output_path}")


def is_test_mode():
    """Check if script is run in test mode."""
    test_flags = ['--test', '-t', 'test']
    return any(flag in sys.argv for flag in test_flags)


def main():
    start_time = time.time()
    
    test_mode = is_test_mode()
    
    print("🎨 PDF Highlight Extractor - BALANCED PRECISION")
    print("✅ More inclusive extraction (40% overlap vs 75%)")
    print("✅ Small boundary expansion (+2 pixels)")
    print("✅ Better word capture at highlight edges")
    print("✅ Detailed extraction logging")
    print("✅ Smart hyphenation merging")
    
    if test_mode:
        print("🧪 TEST MODE: Using defaults")
        print("✅ Default file: /mnt/c/Users/admin/Downloads/test2.pdf")
        print("✅ Skipping JSON/CSV output")
    else:
        print("🔧 FULL MODE: Interactive prompts")
    
    print()
    
    if test_mode:
        default_pdf = "/mnt/c/Users/admin/Downloads/test2.pdf"
        pdf_path = default_pdf
        print(f"📄 Using default: {pdf_path}")
    else:
        pdf_input = input("📄 PDF file path: ").strip('"')
        if not pdf_input:
            print("❌ No file specified!")
            return
        pdf_path = pdf_input
    
    if not Path(pdf_path).exists():
        print("❌ File not found!")
        return
    
    output_json = ""
    output_csv = ""
    
    if test_mode:
        print("📋 Test mode: Display only (no file output)")
    else:
        print("\n📤 Output options:")
        output_json = input("💾 JSON file (Enter to skip): ").strip('"')
        output_csv = input("📊 CSV file (Enter to skip): ").strip('"')
    
    # Process
    extractor = PDFHighlightExtractor(pdf_path)
    annotations, highlights = extractor.extract_all_highlights()
    
    # Display results
    extractor.display_results()
    
    # Save files (only in full mode and if specified)
    if not test_mode:
        if output_json:
            extractor.save_to_json(annotations, highlights, output_json)
        if output_csv:
            extractor.save_to_csv(annotations, highlights, output_csv)
        
        if not output_json and not output_csv:
            print("\n📋 Display only - no files saved")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\n⏱️  Processing completed in {elapsed_time:.2f} seconds")
    
    if test_mode:
        print("\n🧪 Test mode completed. Use without --test flag for full options.")


if __name__ == '__main__':
    main()
