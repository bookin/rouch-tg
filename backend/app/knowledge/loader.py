"""Knowledge base loader - parses all files from terms/"""
from pathlib import Path
from typing import List, Dict
import re
from app.models.knowledge import KnowledgeItem, Correlation, Quote, Concept


class KnowledgeLoader:
    """Loads and parses knowledge base from terms/ directory"""
    
    def __init__(self, knowledge_dir: Path | str):
        self.knowledge_dir = Path(knowledge_dir)
        
    async def load_all(self) -> List[KnowledgeItem]:
        """Load all knowledge items from terms/"""
        items = []
        
        # 1. Correlations from diamond-correlations-table.md
        items.extend(await self._load_correlations())
        
        # 2. Concepts from diamond-concepts.md
        items.extend(await self._load_concepts())
        
        # 3. Quotes from *-quotes.md files
        items.extend(await self._load_quotes())
        
        # 4. Practices from yoga-*.md
        items.extend(await self._load_practices())
        
        # 5. Rules from karma-concepts.md
        items.extend(await self._load_rules())
        
        return items
    
    async def _load_correlations(self) -> List[KnowledgeItem]:
        """Parse correlation table"""
        file_path = self.knowledge_dir / "diamond-correlations-table.md"
        if not file_path.exists():
            return []
        
        content = file_path.read_text(encoding='utf-8')
        correlations = []
        
        # Parse by sections with ## headers
        sections = re.split(r'\n## ', content)
        
        for section in sections[1:]:  # Skip first (before first ##)
            lines = section.split('\n')
            section_name = lines[0].strip()
            
            # Skip non-correlation sections
            if any(skip in section_name.lower() for skip in ['таблица', 'формула', 'ключевые', 'схема']):
                continue
            
            # Find table rows
            table_rows = [line for line in lines if line.strip().startswith('|') and '---' not in line]
            
            for row in table_rows[1:]:  # Skip header
                cells = [cell.strip() for cell in row.split('|')[1:-1]]
                if len(cells) >= 3:
                    problem = cells[1] if len(cells) > 1 else ""
                    cause = cells[2] if len(cells) > 2 else ""
                    solution = cells[3] if len(cells) > 3 else ""
                    
                    if problem and solution:
                        correlations.append(KnowledgeItem(
                            type="correlation",
                            content=f"Проблема: {problem}\nПричина: {cause}\nРешение: {solution}",
                            source="diamond-correlations-table.md",
                            metadata={
                                "problem": problem,
                                "cause": cause,
                                "solution": solution,
                                "category": self._categorize_problem(section_name)
                            }
                        ))
        
        return correlations
    
    async def _load_concepts(self) -> List[KnowledgeItem]:
        """Load core concepts from diamond-concepts.md"""
        file_path = self.knowledge_dir / "diamond-concepts.md"
        if not file_path.exists():
            return []
        
        content = file_path.read_text(encoding='utf-8')
        concepts = []
        
        # Parse by ## headers
        sections = re.split(r'\n## ', content)
        
        for section in sections[1:]:
            lines = section.split('\n')
            title = lines[0].strip()
            text = '\n'.join(lines[1:]).strip()
            
            if text:
                concepts.append(KnowledgeItem(
                    type="concept",
                    content=f"# {title}\n\n{text}",
                    source="diamond-concepts.md",
                    metadata={"title": title, "category": self._categorize_concept(title)}
                ))
        
        return concepts
    
    async def _load_quotes(self) -> List[KnowledgeItem]:
        """Load quotes from *-quotes.md files"""
        quotes = []
        
        for file_name in ["diamond-quotes.md", "karma-quotes.md"]:
            file_path = self.knowledge_dir / file_name
            if not file_path.exists():
                continue
            
            content = file_path.read_text(encoding='utf-8')
            
            # Parse quotes - look for quoted text or bullet points
            lines = content.split('\n')
            current_quote = None
            current_context = None
            
            for line in lines:
                line = line.strip()
                
                # Section headers (context)
                if line.startswith('### '):
                    current_context = line.replace('### ', '').strip()
                    continue
                
                # Quote lines (start with > or -)
                if line.startswith('>') or line.startswith('- "') or line.startswith('"'):
                    quote_text = line.lstrip('>-" ').rstrip('"')
                    
                    if quote_text:
                        quotes.append(KnowledgeItem(
                            type="quote",
                            content=quote_text,
                            source=file_name,
                            metadata={
                                "context": current_context,
                                "tags": self._extract_quote_tags(quote_text, current_context)
                            }
                        ))
        
        return quotes
    
    async def _load_practices(self) -> List[KnowledgeItem]:
        """Load practices from yoga-concepts.md and karma-concepts.md"""
        practices = []
        
        # Yoga practices
        yoga_file = self.knowledge_dir / "yoga-concepts.md"
        if yoga_file.exists():
            content = yoga_file.read_text(encoding='utf-8')
            
            # Find the 10 exercises section
            exercises_section = re.search(r'## Десять упражнений комплекса(.*?)(?=##|$)', content, re.DOTALL)
            if exercises_section:
                exercises_text = exercises_section.group(1)
                
                # Parse each exercise (### headers)
                exercises = re.split(r'\n### ', exercises_text)
                for ex in exercises[1:]:
                    lines = ex.split('\n')
                    name = lines[0].strip()
                    description = '\n'.join(lines[1:]).strip()
                    
                    practices.append(KnowledgeItem(
                        type="practice",
                        content=f"# {name}\n\n{description}",
                        source="yoga-concepts.md",
                        metadata={
                            "name": name,
                            "category": "yoga",
                            "duration": self._extract_duration(name)
                        }
                    ))
        
        # Meditation practices from karma-concepts.md
        karma_file = self.knowledge_dir / "karma-concepts.md"
        if karma_file.exists():
            content = karma_file.read_text(encoding='utf-8')
            
            # Find meditation section
            meditation_section = re.search(r'### 2. Начните делать медитацию(.*?)(?=###|$)', content, re.DOTALL)
            if meditation_section:
                practices.append(KnowledgeItem(
                    type="practice",
                    content=meditation_section.group(0),
                    source="karma-concepts.md",
                    metadata={"name": "Медитация", "category": "meditation", "duration": 10}
                ))
        
        return practices
    
    async def _load_rules(self) -> List[KnowledgeItem]:
        """Load 8 rules from karma-concepts.md"""
        file_path = self.knowledge_dir / "karma-concepts.md"
        if not file_path.exists():
            return []
        
        content = file_path.read_text(encoding='utf-8')
        rules = []
        
        # Find the 8 rules section
        rules_section = re.search(r'## 8 Правил Кармического Менеджмента(.*?)(?=##|$)', content, re.DOTALL)
        if not rules_section:
            return []
        
        rules_text = rules_section.group(1)
        
        # Parse each rule
        individual_rules = re.findall(r'### Правило №(\d+): (.*?)\n(.*?)(?=###|$)', rules_text, re.DOTALL)
        
        for number, title, content_text in individual_rules:
            rules.append(KnowledgeItem(
                type="rule",
                content=f"Правило #{number}: {title}\n\n{content_text.strip()}",
                source="karma-concepts.md",
                metadata={"number": int(number), "title": title}
            ))
        
        return rules
    
    def _categorize_problem(self, section_name: str) -> str:
        """Categorize problem by section name"""
        categories = {
            "финанс": "finance",
            "имущ": "assets",
            "авторит": "authority",
            "отношен": "relationships",
            "решени": "decisions",
            "концентр": "concentration",
            "конкурен": "competition",
            "проект": "projects",
            "здоров": "health",
            "эмоц": "emotions"
        }
        
        section_lower = section_name.lower()
        for key, value in categories.items():
            if key in section_lower:
                return value
        
        return "general"
    
    def _categorize_concept(self, title: str) -> str:
        """Categorize concept by title"""
        if "пустот" in title.lower() or "потенциал" in title.lower():
            return "emptiness"
        elif "отпечат" in title.lower() or "карм" in title.lower():
            return "imprints"
        elif "правил" in title.lower() or "закон" in title.lower():
            return "rules"
        elif "практик" in title.lower() or "упражн" in title.lower():
            return "practices"
        else:
            return "concept"
    
    def _extract_quote_tags(self, quote_text: str, context: str | None) -> List[str]:
        """Extract tags for quote search"""
        tags = []
        
        keywords = {
            "богатств": "wealth",
            "даяни": "giving",
            "щедр": "generosity",
            "пустот": "emptiness",
            "отпечат": "imprints",
            "карм": "karma",
            "жизн": "life",
            "смерт": "death",
            "мудрост": "wisdom",
            "терпени": "patience"
        }
        
        text = (quote_text + " " + (context or "")).lower()
        for keyword, tag in keywords.items():
            if keyword in text:
                tags.append(tag)
        
        return tags
    
    def _extract_duration(self, name: str) -> int:
        """Extract duration in minutes from practice name"""
        match = re.search(r'(\d+)\s*мин', name)
        if match:
            return int(match.group(1))
        return 30  # Default
