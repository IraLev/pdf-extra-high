import pdfplumber
import fitz  # PyMuPDF
import json
from colorama import init, Fore, Back, Style
import pandas as pd
from pathlib import Path
import re

# Initialize colorama for colored terminal output
init(autoreset=True)

class PDFHighlightExtractor:
    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.annotations = []
        self.highlights = []

    def extract_annotation_highlights(self):
        """Extract ALL types of annotations with improved processing."""
        annotations = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                print(f"📄 Processing annotations...")
                for page_num, page in enumerate(pdf.pages, 1):
                    if hasattr(page, 'annots') and page.annots:
                        page_annotations = 0
                        for i, annot in enumerate(page.annots):
                            try:
                                annot_type = annot.get('subtype', 'Unknown')
                                
                                # Process all annotation types
                                if annot_type in ['Highlight', 'Squiggly', 'StrikeOut', 'Underline', 'FreeText', 'Text']:
                                    rect = annot.get('rect', [])
                                    
                                    # Try multiple text extraction methods
                                    text = self._get_annotation_text(page, annot, rect)
                                    color = self._get_color_from_annot(annot)
                                    
                                    if text and text.strip():
                                        annotations.append({
                                            'page': page_num,
                                            'text': self._clean_text(text),
                                            'color': color,
                                            'type': f'annotation_{annot_type.lower()}',
                                            'coordinates': rect,
                                            'y_position': rect[1] if len(rect) >= 4 else 0
                                        })
                                        page_annotations += 1
                            except Exception as e:
                                continue
                        
                        if page_annotations > 0:
                            print(f"  ✅ Page {page_num}: Found {page_annotations} annotations")
            
            print(f"  📊 Total annotations: {len(annotations)}")
        except Exception as e:
            print(f"❌ Error reading annotations: {e}")
        
        return annotations

    def _get_annotation_text(self, page, annot, rect):
        """Try multiple methods to extract annotation text."""
        # Method 1: From annotation contents
        text = annot.get('contents', '').strip()
        if text:
            return text
        
        # Method 2: From rect area
        if rect and len(rect) == 4:
            try:
                x0, y0, x1, y1 = rect
                cropped = page.crop((x0-1, y0-1, x1+1, y1+1))
                text = cropped.extract_text()
                if text and text.strip():
                    return text.strip()
            except:
                pass
        
        # Method 3: From annotation object properties
        for prop in ['label', 'title', 'subject']:
            text = annot.get(prop, '').strip()
            if text:
                return text
        
        return ""

    def extract_background_highlights(self):
        """Extract background highlights with word completion."""
        highlights = []
        try:
            print(f"\n🎨 Processing highlights...")
            doc = fitz.open(str(self.pdf_path))
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_highlights = 0
                
                # Get all text words on the page for word completion
                all_words = page.get_text("words")  # [(x0, y0, x1, y1, "word", block_no, line_no, word_no)]
                
                annotations = page.annots()
                for annot in annotations:
                    try:
                        if annot.type[1] == 'Highlight':
                            # Get color information
                            colors = annot.colors
                            color_name = self._analyze_highlight_color(colors)
                            
                            if color_name != 'unknown':
                                # Extract text from highlighted area
                                rect = annot.rect
                                highlight_text = self._extract_text_from_rect_pymupdf(page, rect)
                                
                                if highlight_text and len(highlight_text.strip()) > 2:
                                    # Complete partial words at start and end
                                    completed_text = self._complete_partial_words(highlight_text, rect, all_words)
                                    clean_text = self._clean_text(completed_text)
                                    
                                    # Create highlight entry
                                    highlight_entry = {
                                        'page': page_num + 1,
                                        'text': clean_text,
                                        'color': color_name,
                                        'type': 'highlight',
                                        'coordinates': list(rect),
                                        'y_position': rect.y0
                                    }
                                    
                                    highlights.append(highlight_entry)
                                    page_highlights += 1
                    except Exception as e:
                        continue
                
                if page_highlights > 0:
                    print(f"  ✅ Page {page_num + 1}: Found {page_highlights} highlights")
                    
            doc.close()
            print(f"  📊 Total highlights: {len(highlights)}")
        except Exception as e:
            print(f"❌ Error reading highlights: {e}")
        
        return highlights

    def _complete_partial_words(self, highlight_text, rect, all_words):
        """Complete partial words at the beginning and end of highlights."""
        if not highlight_text or not all_words:
            return highlight_text
        
        words = highlight_text.split()
        if not words:
            return highlight_text
        
        first_word = words[0]
        last_word = words[-1]
        
        # Find words that intersect with the highlight rectangle
        highlight_rect = fitz.Rect(rect)
        nearby_words = []
        
        for word_info in all_words:
            word_rect = fitz.Rect(word_info[:4])
            word_text = word_info[4]
            
            # Check if word is near the highlight area (within expanded boundaries)
            expanded_rect = fitz.Rect(
                highlight_rect.x0 - 50,  # Expand left
                highlight_rect.y0 - 5,   # Expand up
                highlight_rect.x1 + 50,  # Expand right
                highlight_rect.y1 + 5    # Expand down
            )
            
            if word_rect.intersects(expanded_rect):
                nearby_words.append((word_rect, word_text))
        
        # Sort by position (left to right, top to bottom)
        nearby_words.sort(key=lambda x: (x[0].y0, x[0].x0))
        
        # Complete first word if it seems partial
        if len(first_word) >= 3 and self._is_likely_partial(first_word):
            completed_first = self._find_complete_word(first_word, nearby_words, 'start')
            if completed_first and completed_first != first_word:
                words[0] = completed_first
                print(f"    🔧 Completed first word: '{first_word}' → '{completed_first}'")
        
        # Complete last word if it seems partial
        if len(last_word) >= 3 and self._is_likely_partial(last_word):
            completed_last = self._find_complete_word(last_word, nearby_words, 'end')
            if completed_last and completed_last != last_word:
                words[-1] = completed_last
                print(f"    🔧 Completed last word: '{last_word}' → '{completed_last}'")
        
        return ' '.join(words)

    def _is_likely_partial(self, word):
        """Check if a word is likely partial/incomplete."""
        if not word:
            return False
        
        # Common indicators of partial words
        partial_indicators = [
            len(word) < 3,  # Very short
            word.endswith('-'),  # Hyphenated break
            not word.isalpha() and not word[-1].isalpha(),  # Ends with punctuation
            word.lower() in ['the', 'and', 'of', 'to', 'in', 'for', 'with'],  # Complete common words
        ]
        
        # If it's a common complete word, it's not partial
        if word.lower() in ['the', 'and', 'of', 'to', 'in', 'for', 'with', 'a', 'an', 'is', 'are', 'was', 'were']:
            return False
        
        # Check for incomplete endings (consonant clusters that suggest more letters)
        if len(word) >= 4:
            ending = word[-2:].lower()
            incomplete_endings = ['th', 'st', 'nd', 'rd', 'ch', 'sh', 'nt', 'mp', 'ck', 'ng']
            if any(word.lower().endswith(end) for end in incomplete_endings):
                return True
        
        # Check if it doesn't end with typical word endings
        common_endings = ['ed', 'ing', 'er', 'est', 'ly', 'ion', 'tion', 'ment', 'ness', 'ful', 'less', 'able', 'ible']
        if len(word) >= 4 and not any(word.lower().endswith(end) for end in common_endings):
            return True
        
        return False

    def _find_complete_word(self, partial_word, nearby_words, position):
        """Find the complete word that contains the partial word."""
        partial_lower = partial_word.lower()
        
        candidates = []
        
        for word_rect, full_word in nearby_words:
            full_word_lower = full_word.lower()
            
            if position == 'start':
                # For start position, the partial word should be at the end of the complete word
                if full_word_lower.endswith(partial_lower) and len(full_word) > len(partial_word):
                    candidates.append((full_word, len(full_word)))
            elif position == 'end':
                # For end position, the partial word should be at the start of the complete word
                if full_word_lower.startswith(partial_lower) and len(full_word) > len(partial_word):
                    candidates.append((full_word, len(full_word)))
        
        # Return the longest candidate (most likely to be the complete word)
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return partial_word

    def _extract_text_from_rect_pymupdf(self, page, rect):
        """Extract text from rectangle using multiple PyMuPDF methods."""
        try:
            # Method 1: Direct text extraction
            text = page.get_text("text", clip=rect)
            if text and text.strip():
                return text.strip()
            
            # Method 2: Textbox method
            text = page.get_textbox(rect)
            if text and text.strip():
                return text.strip()
            
            # Method 3: Expanded rectangle
            expanded_rect = fitz.Rect(rect.x0 - 2, rect.y0 - 2, rect.x1 + 2, rect.y1 + 2)
            text_dict = page.get_text("dict", clip=expanded_rect)
            
            text_parts = []
            for block in text_dict.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span["text"].strip():
                                text_parts.append(span["text"])
            
            return " ".join(text_parts)
        except:
            return ""

    def _analyze_highlight_color(self, colors):
        """Analyze highlight color with improved detection."""
        if not colors:
            return 'unknown'
        
        # Check fill color first (highlight background)
        if 'fill' in colors and colors['fill']:
            return self._rgb_to_color_name(colors['fill'])
        elif 'stroke' in colors and colors['stroke']:
            return self._rgb_to_color_name(colors['stroke'])
        
        return 'unknown'

    def _get_color_from_annot(self, annot):
        """Get color from pdfplumber annotation."""
        try:
            color = annot.get('color', [])
            if color:
                return self._rgb_to_color_name(color)
        except:
            pass
        return 'unknown'

    def _rgb_to_color_name(self, rgb):
        """Convert RGB values to color names with improved precision."""
        if not rgb or len(rgb) < 3:
            return 'unknown'
        
        r, g, b = rgb[:3]
        
        # Precise color detection
        if r > 0.7 and g > 0.7 and b < 0.6:
            return 'yellow'
        elif r < 0.6 and g > 0.7 and b < 0.6:
            return 'green'
        elif r < 0.6 and g < 0.8 and b > 0.7:
            return 'blue'
        elif r > 0.7 and g < 0.6 and b > 0.7:
            return 'pink'
        elif r > 0.8 and g > 0.5 and b < 0.5:
            return 'orange'
        elif r > 0.7 and g < 0.5 and b < 0.5:
            return 'red'
        elif r < 0.5 and g > 0.7 and b > 0.7:
            return 'cyan'
        else:
            return f'rgb({r:.2f},{g:.2f},{b:.2f})'

    def _clean_text(self, text):
        """Clean and normalize text."""
        if not text:
            return ""
        
        try:
            # Remove extra whitespace and normalize
            text = re.sub(r'\s+', ' ', text.strip())
            # Remove line break hyphens
            text = re.sub(r'-\s+', '', text)
            # Fix punctuation spacing
            text = re.sub(r'\s+([.,;:!?])', r'\1', text)
            return text
        except:
            return str(text) if text else ""

    def _smart_deduplicate(self, items):
        """Smart deduplication that merges similar highlights."""
        if not items:
            return items
        
        # Sort by page and position
        items.sort(key=lambda x: (x['page'], x['y_position'], len(x['text'])))
        
        unique_items = []
        for item in items:
            is_duplicate = False
            
            for existing in unique_items:
                # Check if this is a duplicate or subset
                if (item['page'] == existing['page'] and 
                    item['color'] == existing['color'] and
                    abs(item['y_position'] - existing['y_position']) < 10):
                    
                    # Check text similarity
                    item_text = item['text'].lower().strip()
                    existing_text = existing['text'].lower().strip()
                    
                    # If one is substring of another, keep the longer one
                    if item_text in existing_text:
                        is_duplicate = True
                        break
                    elif existing_text in item_text:
                        # Replace existing with longer text
                        existing['text'] = item['text']
                        is_duplicate = True
                        break
                    # If very similar (90% overlap), it's a duplicate
                    elif self._text_similarity(item_text, existing_text) > 0.9:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_items.append(item)
        
        return unique_items

    def _text_similarity(self, text1, text2):
        """Calculate text similarity ratio."""
        if not text1 or not text2:
            return 0
        
        # Simple word-based similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0

    def extract_all_highlights(self):
        """Extract and process all highlights and annotations."""
        print("🔍 PDF Highlight & Annotation Extractor")
        print("=" * 50)
        
        # Extract annotations
        self.annotations = self.extract_annotation_highlights()
        
        # Extract highlights  
        self.highlights = self.extract_background_highlights()
        
        # Smart deduplication
        self.highlights = self._smart_deduplicate(self.highlights)
        
        print(f"\n✨ Processing complete!")
        print(f"   📝 Annotations: {len(self.annotations)}")
        print(f"   🎨 Highlights: {len(self.highlights)}")
        
        return self.annotations, self.highlights

    def sort_by_position(self, items):
        """Sort items by page, then top to bottom."""
        return sorted(items, key=lambda x: (x['page'], x['y_position']))

    def save_to_json(self, annotations, highlights, output_path):
        """Save results to JSON file."""
        data = {
            'annotations': annotations,
            'highlights': highlights,
            'summary': {
                'total_annotations': len(annotations),
                'total_highlights': len(highlights),
                'annotation_colors': list(set(a['color'] for a in annotations)),
                'highlight_colors': list(set(h['color'] for h in highlights))
            }
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved to {output_path}")

    def save_to_csv(self, annotations, highlights, output_path):
        """Save results to CSV file."""
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

    def display_results(self):
        """Display results with clean formatting."""
        
        print("\n" + "="*60)
        print("📋 EXTRACTION RESULTS")
        print("="*60)
        
        # Display Annotations
        if self.annotations:
            sorted_annotations = self.sort_by_position(self.annotations)
            print(f"\n📝 ANNOTATIONS ({len(sorted_annotations)} items)")
            print("-" * 40)
            
            for i, item in enumerate(sorted_annotations, 1):
                color_code = self._get_color_code(item['color'])
                print(f"\n{i:2d}. Page {item['page']} | {color_code}{item['color'].upper()}{Style.RESET_ALL}")
                print(f"    Type: {item['type']}")
                print(f"    Text: \"{item['text']}\"")
        else:
            print(f"\n📝 ANNOTATIONS: None found")
        
        # Display Highlights  
        if self.highlights:
            sorted_highlights = self.sort_by_position(self.highlights)
            print(f"\n🎨 BACKGROUND HIGHLIGHTS ({len(sorted_highlights)} items)")
            print("-" * 40)
            
            for i, item in enumerate(sorted_highlights, 1):
                color_code = self._get_color_code(item['color'])
                print(f"\n{i:2d}. Page {item['page']} | {color_code}{item['color'].upper()}{Style.RESET_ALL}")
                print(f"    Text: \"{item['text']}\"")
        else:
            print(f"\n🎨 BACKGROUND HIGHLIGHTS: None found")
        
        print("\n" + "="*60)

    def _get_color_code(self, color_name):
        """Get terminal color code for display."""
        color_map = {
            'yellow': Back.YELLOW + Fore.BLACK,
            'green': Back.GREEN + Fore.BLACK,
            'blue': Back.BLUE + Fore.WHITE,
            'red': Back.RED + Fore.WHITE,
            'pink': Back.MAGENTA + Fore.WHITE,
            'orange': Back.YELLOW + Fore.RED,
            'cyan': Back.CYAN + Fore.BLACK,
            'unknown': Back.WHITE + Fore.BLACK
        }
        return color_map.get(color_name, Back.WHITE + Fore.BLACK)


def main():
    print("🎨 PDF Highlight & Annotation Extractor")
    print("🚀 Enhanced with smart word completion and deduplication")
    print()
    
    # Get PDF file path
    pdf_path = input("📄 Enter PDF file path: ").strip('"')
    
    if not Path(pdf_path).exists():
        print("❌ File not found!")
        return
    
    # Get output options
    print("\n📤 Output Options:")
    output_json = input("💾 JSON file (or Enter to skip): ").strip('"')
    output_csv = input("📊 CSV file (or Enter to skip): ").strip('"')
    
    # Process PDF
    extractor = PDFHighlightExtractor(pdf_path)
    annotations, highlights = extractor.extract_all_highlights()
    
    # Display results
    extractor.display_results()
    
    # Save results
    if output_json:
        extractor.save_to_json(annotations, highlights, output_json)
    if output_csv:
        extractor.save_to_csv(annotations, highlights, output_csv)


if __name__ == '__main__':
    main()
