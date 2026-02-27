"""Knowledge base loader - parses all files from terms/"""
from pathlib import Path
from typing import List, Dict
import re
import csv
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
        # 1b. Extended correlations from diamond-correlations-extended.md
        items.extend(await self._load_extended_correlations())
        
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
                                "category": self._categorize_problem(section_name),
                                # Обобщённый тип отпечатка / паттерна, извлечённый из причины
                                "problem_type": self._extract_problem_type(cause),
                                # Источник внутри корреляций: базовая таблица
                                "source_type": "base",
                            }
                        ))
        
        return correlations
    
    async def _load_extended_correlations(self) -> List[KnowledgeItem]:
        """Parse extended correlation tables with additional fields"""
        file_path = self.knowledge_dir / "diamond-correlations-extended.md"
        if not file_path.exists():
            return []
        
        content = file_path.read_text(encoding="utf-8")
        correlations: List[KnowledgeItem] = []
        
        # Split by sections starting with level-2 headers (## ...)
        sections = re.split(r"\n## ", content)
        
        for section in sections[1:]:  # Skip header part before first section
            lines = section.split("\n")
            if not lines:
                continue
            section_name = lines[0].strip()
            
            # Find table rows (lines starting with '|' but not separator row with '---')
            table_rows = [line for line in lines if line.strip().startswith("|") and "---" not in line]
            if len(table_rows) < 2:
                continue
            
            # Skip header row (first data row is after it)
            for row in table_rows[1:]:
                cells = [cell.strip() for cell in row.split("|")[1:-1]]
                # Expected schema:
                # № | Проблема | Сфера | Импринт | Качество | Решение | Партнёры | Принцип
                if len(cells) < 8:
                    continue
                number = cells[0]
                problem = cells[1]
                sphere = cells[2]
                imprint = cells[3]
                quality = cells[4]
                solution = cells[5]
                partners = cells[6]
                principle = cells[7]
                
                cause = imprint
                if not problem or not solution:
                    continue
                
                category = self._category_from_sphere(sphere, section_name)
                
                correlations.append(
                    KnowledgeItem(
                        type="correlation",
                        content=(
                            f"Проблема: {problem}\n"
                            f"Причина: {cause}\n"
                            f"Решение: {solution}"
                        ),
                        source="diamond-correlations-extended.md",
                        metadata={
                            "problem": problem,
                            "cause": cause,
                            "solution": solution,
                            "category": category,
                            "sphere": sphere,
                            "imprint": imprint,
                            "quality": quality,
                            "partners": partners,
                            "principle": principle,
                            "number": number,
                            # Обобщённый тип отпечатка (первая фраза из колонки "Импринт")
                            "problem_type": self._extract_problem_type(imprint),
                            # Источник внутри корреляций: расширенная таблица
                            "source_type": "extended",
                        },
                    )
                )
        
        return correlations
    
    async def _load_concepts(self) -> List[KnowledgeItem]:
        """Load core concepts from CSV if available, otherwise from diamond-concepts.md."""
        concepts: List[KnowledgeItem] = []

        # 1. Try CSV-based concepts first
        csv_path = self.knowledge_dir / "concepts.csv"
        if csv_path.exists():
            with csv_path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    title = (row.get("title") or "").strip()
                    if not title:
                        continue
                    category = (row.get("category") or "").strip() or self._categorize_concept(title)
                    body = (row.get("content") or "").strip()
                    source = (row.get("source") or "concepts.csv").strip()

                    content = f"# {title}\n\n{body}" if body else title

                    concepts.append(
                        KnowledgeItem(
                            type="concept",
                            content=content,
                            source=source,
                            metadata={"title": title, "category": category},
                        )
                    )

            return concepts

        # 2. Fallback: старый парсинг diamond-concepts.md
        file_path = self.knowledge_dir / "diamond-concepts.md"
        if not file_path.exists():
            return []

        content = file_path.read_text(encoding="utf-8")
        concepts = []

        # Parse by ## headers
        sections = re.split(r"\n## ", content)

        for section in sections[1:]:
            lines = section.split("\n")
            title = lines[0].strip()
            text = "\n".join(lines[1:]).strip()

            if text:
                concepts.append(
                    KnowledgeItem(
                        type="concept",
                        content=f"# {title}\n\n{text}",
                        source="diamond-concepts.md",
                        metadata={
                            "title": title,
                            "category": self._categorize_concept(title),
                        },
                    )
                )

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
        """Load practices from CSV if available, otherwise fall back to markdown parsing."""
        practices: List[KnowledgeItem] = []

        # 1. Try CSV-based practices first
        csv_path = self.knowledge_dir / "practices.csv"
        if csv_path.exists():
            with csv_path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    name = (row.get("name") or "").strip()
                    if not name:
                        continue
                    practice_id = (row.get("id") or "").strip()
                    if not practice_id:
                        continue
                    category = (row.get("category") or "").strip()
                    duration_raw = (row.get("duration_min") or "").strip()
                    try:
                        duration = int(duration_raw) if duration_raw else 0
                    except ValueError:
                        duration = 0

                    # Parse structured fields
                    difficulty_raw = (row.get("difficulty") or "1").strip()
                    try:
                        difficulty = int(difficulty_raw)
                    except ValueError:
                        difficulty = 1
                    physical_intensity = (row.get("physical_intensity") or "low").strip()
                    requires_morning = (row.get("requires_morning") or "false").strip().lower() == "true"
                    requires_silence = (row.get("requires_silence") or "false").strip().lower() == "true"
                    max_completions_raw = (row.get("max_completions_per_day") or "1").strip()
                    try:
                        max_completions = int(max_completions_raw)
                    except ValueError:
                        max_completions = 1
                    habit_streak_raw = (row.get("habit_min_streak_days") or "14").strip()
                    try:
                        habit_min_streak = int(habit_streak_raw)
                    except ValueError:
                        habit_min_streak = 14
                    habit_score_raw = (row.get("habit_min_score") or "70").strip()
                    try:
                        habit_min_score = int(habit_score_raw)
                    except ValueError:
                        habit_min_score = 70

                    steps_raw = (row.get("steps") or "").strip()
                    steps = [s.strip() for s in steps_raw.split("|") if s.strip()] if steps_raw else []

                    contra_raw = (row.get("contraindications") or "").strip()
                    contraindications = [c.strip() for c in contra_raw.split(",") if c.strip() and c.strip() != "none"]

                    benefits = (row.get("benefits") or "").strip()
                    tags_raw = (row.get("tags") or "").strip()
                    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

                    # Build content for Qdrant embedding (name + benefits + steps summary)
                    content_parts = [name]
                    if benefits:
                        content_parts.append(benefits)
                    if steps:
                        content_parts.append(" | ".join(steps[:5]))
                    if tags:
                        content_parts.append(", ".join(tags))
                    content = ". ".join(content_parts)

                    practices.append(
                        KnowledgeItem(
                            id=practice_id,
                            type="practice",
                            content=content,
                            source="practices.csv",
                            metadata={
                                "id": practice_id,
                                "name": name,
                                "category": category,
                                "duration": duration,
                                "difficulty": difficulty,
                                "physical_intensity": physical_intensity,
                                "requires_morning": requires_morning,
                                "requires_silence": requires_silence,
                                "max_completions_per_day": max_completions,
                                "habit_min_streak_days": habit_min_streak,
                                "habit_min_score": habit_min_score,
                                "steps": steps,
                                "contraindications": contraindications,
                                "benefits": benefits,
                                "tags": tags,
                            },
                        )
                    )

            return practices

        # 2. Fallback: старый парсинг markdown (для совместимости)
        # Yoga practices
        yoga_file = self.knowledge_dir / "yoga-concepts.md"
        if yoga_file.exists():
            content = yoga_file.read_text(encoding="utf-8")

            # Find the 10 exercises section
            exercises_section = re.search(
                r"## Десять упражнений комплекса(.*?)(?=##|$)",
                content,
                re.DOTALL,
            )
            if exercises_section:
                exercises_text = exercises_section.group(1)

                # Parse each exercise (### headers)
                exercises = re.split(r"\n### ", exercises_text)
                for i, ex in enumerate(exercises[1:], practice_counter):
                    lines = ex.split("\n")
                    name = lines[0].strip()
                    description = "\n".join(lines[1:]).strip()

                    practices.append(
                        KnowledgeItem(
                            type="practice",
                            content=f"# {name}\n\n{description}",
                            source="yoga-concepts.md",
                            metadata={
                                "id": str(i),  # Добавляем ID
                                "name": name,
                                "category": "yoga",
                                "duration": self._extract_duration(name),
                            },
                        )
                    )

        # Meditation practices from karma-concepts.md
        karma_file = self.knowledge_dir / "karma-concepts.md"
        if karma_file.exists():
            content = karma_file.read_text(encoding="utf-8")

            # Find meditation section
            meditation_section = re.search(
                r"### 2. Начните делать медитацию(.*?)(?=###|$)",
                content,
                re.DOTALL,
            )
            if meditation_section:
                practices.append(
                    KnowledgeItem(
                        type="practice",
                        content=meditation_section.group(0),
                        source="karma-concepts.md",
                        metadata={
                            "name": "Медитация",
                            "category": "meditation",
                            "duration": 10,
                        },
                    )
                )

        return practices
    
    async def _load_rules(self) -> List[KnowledgeItem]:
        """Load rules from CSV if available, otherwise fall back to markdown parsing."""
        rules: List[KnowledgeItem] = []

        # 1. Try CSV-based rules first
        csv_path = self.knowledge_dir / "rules.csv"
        if csv_path.exists():
            with csv_path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    number_raw = (row.get("number") or "").strip()
                    if not number_raw:
                        continue
                    try:
                        number = int(number_raw)
                    except ValueError:
                        continue
                    title = (row.get("title") or "").strip()
                    content = (row.get("content") or "").strip()
                    source = (row.get("source") or "rules.csv").strip()

                    rules.append(
                        KnowledgeItem(
                            type="rule",
                            content=content,
                            source=source,
                            metadata={
                                "number": number,
                                "title": title,
                            },
                        )
                    )

            return rules

        # 2. Fallback: старый парсинг markdown (для совместимости)
        file_path = self.knowledge_dir / "karma-concepts.md"
        if not file_path.exists():
            return []

        content = file_path.read_text(encoding="utf-8")
        rules = []

        # Find the 8 rules section
        rules_section = re.search(
            r"## 8 Правил Кармического Менеджмента(.*?)(?=##|$)",
            content,
            re.DOTALL,
        )
        if not rules_section:
            return []

        rules_text = rules_section.group(1)

        # Parse each rule
        individual_rules = re.findall(
            r"### Правило №(\d+): (.*?)\n(.*?)(?=###|$)",
            rules_text,
            re.DOTALL,
        )

        for number, title, content_text in individual_rules:
            rules.append(
                KnowledgeItem(
                    type="rule",
                    content=f"Правило #{number}: {title}\n\n{content_text.strip()}",
                    source="karma-concepts.md",
                    metadata={"number": int(number), "title": title},
                )
            )

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
    
    def _extract_problem_type(self, text: str | None) -> str:
        """Extract generalized imprint/problem type from free-form text.

        Heuristic: take the first meaningful fragment (before newline or comma).
        This даёт короткий ярлык вроде "Скупость", "Гнев на партнёров",
        который можно использовать как problem_type.
        """
        if not text:
            return ""
        # Берём первую строку
        first_line = str(text).strip().split("\n", 1)[0]
        # Отсекаем всё после точки/воскл./вопросительного знака/точки с запятой
        for sep in [".", "!", "?", ";"]:
            if sep in first_line:
                first_line = first_line.split(sep, 1)[0]
        # И первую часть до запятой как ярлык
        if "," in first_line:
            first_line = first_line.split(",", 1)[0]
        return first_line.strip()
    
    def _category_from_sphere(self, sphere: str, section_name: str) -> str:
        """Map high-level sphere name to correlation category"""
        text = (sphere or "").lower()
        if "финанс" in text or "деньг" in text:
            return "finance"
        if "отношен" in text:
            return "relationships"
        if "здоров" in text:
            return "health"
        if "смысл" in text or "путь" in text:
            return "meaning"
        if "работ" in text or "карьер" in text or "бизнес" in text:
            return "career"
        if "эмоци" in text or "состояни" in text:
            return "emotions"
        
        # Fallback to existing section-based categorization
        return self._categorize_problem(section_name)
    
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
