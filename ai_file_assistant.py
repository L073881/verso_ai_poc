"""
AI File Assistant Module

Parses user intents and generates file content using Cortex AI.
Handles the orchestration between AI, file operations, and git.
"""

import os
import re
import json
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Configure logging - only show warnings and errors
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class ActionType(Enum):
    """Types of actions the AI can perform."""
    CREATE_FILE = "create_file"      # Create a new file with content
    UPDATE_FILE = "update_file"      # Replace entire file content
    EDIT_FILE = "edit_file"          # Make specific targeted edits (change X to Y)
    DELETE_FILE = "delete_file"
    READ_FILE = "read_file"          # Just read/show file content
    CHAT = "chat"                    # Answer questions, have conversations
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """AI-parsed user intent from natural language."""
    action: ActionType
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    content_description: Optional[str] = None
    word_count: Optional[int] = None
    topic: Optional[str] = None
    update_type: Optional[str] = None  # append, prepend, replace
    raw_query: str = ""
    confidence: float = 0.0
    # AI-generated understanding
    ai_summary: Optional[str] = None  # AI's summary of what user wants
    ai_file_purpose: Optional[str] = None  # Why this file is being created
    ai_content_outline: Optional[str] = None  # What content will include
    ai_suggestions: Optional[str] = None  # Any suggestions from AI
    # For targeted edits (EDIT_FILE action)
    edit_instruction: Optional[str] = None  # e.g., "change 'John' to 'Jane'"
    search_text: Optional[str] = None  # Text to find
    replace_text: Optional[str] = None  # Text to replace with
    # For chat responses
    chat_response: Optional[str] = None  # Direct AI response for chat questions


class AIIntentParser:
    """
    AI-powered intent parser that uses Cortex to understand user requests.
    Provides detailed, intelligent parsing of natural language queries.
    """
    
    def __init__(self, cortex_client, model_name: str):
        """
        Initialize AI Intent Parser.
        
        Args:
            cortex_client: Initialized Cortex client
            model_name: Cortex model name to use
        """
        self.client = cortex_client
        self.model_name = model_name
        self.cortex_base = "https://api.cortex.lilly.com"
    
    def parse(self, query: str) -> ParsedIntent:
        """
        Use AI to parse and understand user's natural language query.
        This is the brain of the assistant - it understands EVERYTHING.
        
        Args:
            query: Natural language query from user
        
        Returns:
            ParsedIntent object with AI-extracted information
        """
        prompt = f"""You are Verso AI, an intelligent assistant that understands ANY user request.

Analyze this user request carefully:
"{query}"

Determine what the user wants and provide your analysis in this EXACT format:

ACTION: [One of: create_file / edit_file / update_file / read_file / chat]
FILE_NAME: [filename with extension, or "none" if not applicable]
EDIT_INSTRUCTION: [For edit_file: describe the specific change, e.g., "change Technical Owner from X to Aneesh Madupalli"]
SEARCH_TEXT: [For edit_file: the exact text to find and replace, or "none"]
REPLACE_TEXT: [For edit_file: the exact text to replace with, or "none"]
TOPIC: [the main subject/topic, or "none" for chat]
WORD_COUNT: [number if specified, or "none"]
UPDATE_TYPE: [append / prepend / replace, or "none"]
SUMMARY: [A clear 1-2 sentence summary of what the user wants]
CHAT_RESPONSE: [If ACTION is chat, provide the complete answer to the user's question here. Otherwise "none"]

RULES FOR DETERMINING ACTION:
1. "chat" - When user asks a question, wants information, or is having a conversation
   Examples: "who founded ChatGPT?", "what is machine learning?", "hello"
   → Provide the full answer in CHAT_RESPONSE
   
2. "edit_file" - When user wants to MODIFY SPECIFIC parts of an existing file
   Examples: "in readme.md, change Technical Owner to Aneesh", "update the version to 2.0 in package.json"
   → Extract the file name, what to search for, and what to replace with
   
3. "create_file" - When user wants to CREATE A NEW file
   Examples: "create a new file test.md about LLMs", "make a python script for API calls"
   
4. "update_file" - When user wants to ADD content to file (append/prepend) or REPLACE ALL content
   Examples: "add installation instructions to readme", "append changelog entry"
   
5. "read_file" - When user wants to SEE/READ a file
   Examples: "show me the readme", "what's in config.json?"

IMPORTANT: 
- Be VERY careful to distinguish between edit_file (specific changes) vs update_file (add new content)
- For chat, ALWAYS provide a complete, helpful CHAT_RESPONSE
- Extract exact text for SEARCH_TEXT and REPLACE_TEXT when doing edits

Analyze now:"""

        try:
            response = self.client.post(
                f"{self.cortex_base}/model/ask/{self.model_name}",
                data={"q": prompt}
            )
            response.raise_for_status()
            ai_response = response.json().get("message", "").strip()
            
            # Parse the AI response
            return self._parse_ai_response(ai_response, query)
            
        except Exception as e:
            logger.warning(f"AI intent parsing failed, using fallback: {e}")
            return self._fallback_parse(query)
    
    def _parse_ai_response(self, ai_response: str, original_query: str) -> ParsedIntent:
        """Parse the structured AI response into a ParsedIntent object."""
        lines = ai_response.strip().split('\n')
        parsed_data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                parsed_data[key.strip().upper()] = value.strip()
        
        # Extract action - now includes edit_file and read_file
        action_str = parsed_data.get('ACTION', 'chat').lower().strip()
        action_map = {
            'create_file': ActionType.CREATE_FILE,
            'update_file': ActionType.UPDATE_FILE,
            'edit_file': ActionType.EDIT_FILE,
            'read_file': ActionType.READ_FILE,
            'delete_file': ActionType.DELETE_FILE,
            'chat': ActionType.CHAT
        }
        action = action_map.get(action_str, ActionType.CHAT)
        
        # Extract file name
        file_name = parsed_data.get('FILE_NAME', '')
        if file_name.lower() in ('none', '', 'n/a', 'not specified', 'not applicable'):
            file_name = None
        
        # Extract topic
        topic = parsed_data.get('TOPIC', '')
        if topic.lower() in ('none', '', 'n/a', 'not specified'):
            topic = None
        
        # Extract word count
        word_count_str = parsed_data.get('WORD_COUNT', 'none')
        try:
            word_count = int(re.search(r'\d+', word_count_str).group()) if re.search(r'\d+', word_count_str) else None
        except:
            word_count = None
        
        # Extract update type
        update_type = parsed_data.get('UPDATE_TYPE', 'append').lower()
        if update_type in ('none', '', 'n/a'):
            update_type = 'append' if action == ActionType.UPDATE_FILE else None
        
        # Extract edit-specific fields
        edit_instruction = parsed_data.get('EDIT_INSTRUCTION', '')
        if edit_instruction.lower() in ('none', '', 'n/a'):
            edit_instruction = None
            
        search_text = parsed_data.get('SEARCH_TEXT', '')
        if search_text.lower() in ('none', '', 'n/a'):
            search_text = None
            
        replace_text = parsed_data.get('REPLACE_TEXT', '')
        if replace_text.lower() in ('none', '', 'n/a'):
            replace_text = None
        
        # Extract chat response
        chat_response = parsed_data.get('CHAT_RESPONSE', '')
        if chat_response.lower() in ('none', '', 'n/a'):
            chat_response = None
        
        # Extract AI insights
        ai_summary = parsed_data.get('SUMMARY', '')
        ai_file_purpose = parsed_data.get('PURPOSE', '')
        ai_content_outline = parsed_data.get('CONTENT_OUTLINE', '')
        ai_suggestions = parsed_data.get('SUGGESTIONS', '')
        
        # Calculate confidence
        confidence_str = parsed_data.get('CONFIDENCE', 'high').lower()
        confidence_map = {'high': 0.95, 'medium': 0.75, 'low': 0.5}
        confidence = confidence_map.get(confidence_str, 0.85)
        
        return ParsedIntent(
            action=action,
            file_name=file_name,
            content_description=topic,
            word_count=word_count,
            topic=topic,
            update_type=update_type,
            raw_query=original_query,
            confidence=confidence,
            ai_summary=ai_summary if ai_summary else None,
            ai_file_purpose=ai_file_purpose if ai_file_purpose else None,
            ai_content_outline=ai_content_outline if ai_content_outline else None,
            ai_suggestions=ai_suggestions if ai_suggestions else None,
            edit_instruction=edit_instruction,
            search_text=search_text,
            replace_text=replace_text,
            chat_response=chat_response
        )
    
    def _fallback_parse(self, query: str) -> ParsedIntent:
        """Fallback regex-based parsing if AI fails."""
        query_lower = query.lower()
        
        # Detect action
        if any(kw in query_lower for kw in ['create', 'make', 'add', 'generate', 'write', 'new file']):
            action = ActionType.CREATE_FILE
        elif any(kw in query_lower for kw in ['update', 'modify', 'edit', 'change', 'append']):
            action = ActionType.UPDATE_FILE
        elif any(kw in query_lower for kw in ['delete', 'remove']):
            action = ActionType.DELETE_FILE
        else:
            action = ActionType.CHAT
        
        # Extract filename
        file_match = re.search(r'["\']?([a-zA-Z0-9_\-]+\.(md|txt|py|js|json|yaml|html|css))["\']?', query, re.IGNORECASE)
        file_name = file_match.group(1) if file_match else None
        
        # Extract word count
        word_match = re.search(r'(\d+)\s*words?', query_lower)
        word_count = int(word_match.group(1)) if word_match else None
        
        # Extract topic (everything after 'about', 'regarding', etc.)
        topic_match = re.search(r'(?:about|regarding|on|having|with)\s+(.+?)(?:\s+with\s+\d+|\s*$)', query, re.IGNORECASE)
        topic = topic_match.group(1).strip() if topic_match else None
        
        return ParsedIntent(
            action=action,
            file_name=file_name,
            content_description=topic,
            word_count=word_count,
            topic=topic,
            update_type='append' if action == ActionType.UPDATE_FILE else None,
            raw_query=query,
            confidence=0.6,
            ai_summary=f"Create/update {file_name or 'file'} about {topic or 'specified topic'}",
            ai_file_purpose=None,
            ai_content_outline=None,
            ai_suggestions=None
        )


# Keep old IntentParser for backward compatibility but mark as deprecated
class IntentParser:
    """
    DEPRECATED: Use AIIntentParser instead.
    Legacy regex-based parser kept for backward compatibility.
    """
    
    def parse(self, query: str) -> ParsedIntent:
        """Legacy parse method - use AIIntentParser for better results."""
        query_lower = query.lower()
        
        # Detect action
        if any(kw in query_lower for kw in ['create', 'make', 'add', 'generate', 'write', 'new file']):
            action = ActionType.CREATE_FILE
        elif any(kw in query_lower for kw in ['update', 'modify', 'edit', 'change', 'append']):
            action = ActionType.UPDATE_FILE
        elif any(kw in query_lower for kw in ['delete', 'remove']):
            action = ActionType.DELETE_FILE
        else:
            action = ActionType.CHAT
        
        # Extract filename
        file_match = re.search(r'["\']?([a-zA-Z0-9_\-]+\.(md|txt|py|js|json|yaml|html|css))["\']?', query, re.IGNORECASE)
        file_name = file_match.group(1) if file_match else None
        
        # Extract word count
        word_match = re.search(r'(\d+)\s*words?', query_lower)
        word_count = int(word_match.group(1)) if word_match else None
        
        # Extract topic
        topic_match = re.search(r'(?:about|regarding|on|having|with)\s+(.+?)(?:\s+with\s+\d+|\s*$)', query, re.IGNORECASE)
        topic = topic_match.group(1).strip() if topic_match else None
        
        return ParsedIntent(
            action=action,
            file_name=file_name,
            content_description=topic,
            word_count=word_count,
            topic=topic,
            update_type='append' if action == ActionType.UPDATE_FILE else None,
            raw_query=query,
            confidence=0.6
        )


class ContentGenerator:
    """
    Generates file content using Cortex AI.
    """
    
    def __init__(self, cortex_client, model_name: str):
        """
        Initialize content generator.
        
        Args:
            cortex_client: Initialized Cortex client
            model_name: Cortex model name to use
        """
        self.client = cortex_client
        self.model_name = model_name
        self.cortex_base = "https://api.cortex.lilly.com"
    
    def generate_file_content(
        self,
        topic: str,
        file_type: str = "md",
        word_count: Optional[int] = None,
        additional_instructions: str = ""
    ) -> str:
        """
        Generate file content using AI.
        
        Args:
            topic: Topic/subject for the content
            file_type: File type (md, txt, py, etc.)
            word_count: Target word count
            additional_instructions: Extra instructions for generation
        
        Returns:
            Generated content string
        """
        # Build prompt based on file type
        if file_type in ("md", "markdown"):
            format_instruction = "Format the content as Markdown with proper headings, bullet points, and sections."
        elif file_type == "py":
            format_instruction = "Generate Python code with proper docstrings and comments."
        elif file_type == "txt":
            format_instruction = "Write in plain text format."
        else:
            format_instruction = f"Format appropriately for a .{file_type} file."
        
        word_instruction = f"The content should be approximately {word_count} words." if word_count else ""
        
        prompt = f"""Generate content for a file about: {topic}

{format_instruction}
{word_instruction}
{additional_instructions}

Important: 
- Write comprehensive, well-structured content
- Make it informative and professional
- Do not include any meta-commentary, just the content itself
- Start directly with the content (no "Here is..." or similar phrases)
"""
        
        try:
            response = self.client.post(
                f"{self.cortex_base}/model/ask/{self.model_name}",
                data={"q": prompt}
            )
            response.raise_for_status()
            content = response.json().get("message", "")
            
            # Clean up any leading/trailing whitespace
            content = content.strip()
            
            logger.info(f"Generated content: {len(content)} characters")
            return content
            
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise
    
    def generate_smart_edit(
        self,
        file_content: str,
        user_instruction: str,
        file_name: str
    ) -> Tuple[str, str]:
        """
        Generate a smart edit to existing file content based on user instruction.
        This method asks AI to identify the search/replace strings, then does the replacement in Python.
        This ensures ONLY the targeted change is made.
        
        Args:
            file_content: Current content of the file
            user_instruction: What the user wants to change (e.g., "change Technical Owner to Aneesh")
            file_name: Name of the file being edited
        
        Returns:
            Tuple of (new_content, description_of_change)
        """
        # Show the file content - prefer the end if it's a long file (often contact info is at the end)
        if len(file_content) > 4000:
            # Show first 1500 and last 2500 chars
            content_preview = file_content[:1500] + "\n\n... [middle content omitted] ...\n\n" + file_content[-2500:]
        else:
            content_preview = file_content
        
        prompt = f"""You are a precise text editor. The user wants to make a specific change to a file.

FILE: {file_name}
FILE CONTENT:
---
{content_preview}
---

USER'S REQUEST: "{user_instruction}"

Your task: Identify the EXACT text to find and the EXACT text to replace it with.

CRITICAL RULES:
1. SEARCH text must be copied EXACTLY from the file (character by character, including any trailing spaces)
2. REPLACE text is the new value with the change applied
3. SEARCH and REPLACE must be DIFFERENT - you are making a change!
4. If a field is empty like "- Technical Owner:  " and user wants to fill it with "Aneesh Madupalli", then:
   - SEARCH: - Technical Owner:  
   - REPLACE: - Technical Owner: Aneesh Madupalli
5. DO NOT add trailing colons to names/values
6. Keep formatting consistent with the file

Respond in this EXACT format only:
SEARCH: [copy exact text from file - must exist in the file]
REPLACE: [new text after the change - must be different from SEARCH]
DESCRIPTION: [brief description]

Example 1 - Fill empty field "set Technical Owner to Aneesh Madupalli":
SEARCH: - Technical Owner:  
REPLACE: - Technical Owner: Aneesh Madupalli
DESCRIPTION: Set Technical Owner to Aneesh Madupalli

Example 2 - Change existing value "change version from 1.0 to 2.0":
SEARCH: version: 1.0
REPLACE: version: 2.0
DESCRIPTION: Updated version to 2.0"""

        try:
            response = self.client.post(
                f"{self.cortex_base}/model/ask/{self.model_name}",
                data={"q": prompt}
            )
            response.raise_for_status()
            ai_response = response.json().get("message", "").strip()
            
            # Parse the response to get SEARCH and REPLACE values
            search_text = None
            replace_text = None
            description = "Applied edit"
            
            for line in ai_response.split('\n'):
                line = line.strip()
                if line.startswith('SEARCH:'):
                    search_text = line[7:].strip()
                elif line.startswith('REPLACE:'):
                    replace_text = line[8:].strip()
                elif line.startswith('DESCRIPTION:'):
                    description = line[12:].strip()
            
            if not search_text or not replace_text:
                raise ValueError(f"Could not parse AI response: {ai_response[:200]}")
            
            # Check if search and replace are the same (no actual change)
            if search_text == replace_text:
                raise ValueError(f"SEARCH and REPLACE are identical - no change needed")
            
            # Check if the replacement text already exists in the file
            if replace_text in file_content:
                raise ValueError(f"The file already contains '{replace_text}' - change already applied")
            
            # Check if search text exists in the file
            if search_text not in file_content:
                # Try case-insensitive search
                import re
                pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                match = pattern.search(file_content)
                if match:
                    search_text = match.group()  # Use the actual text from file
                else:
                    # Log what AI returned vs what's in the file for debugging
                    logger.error(f"AI returned SEARCH: '{search_text}'")
                    logger.error(f"File content snippet: '{file_content[300:400]}'")
                    raise ValueError(f"Could not find the text to replace. The AI may have misidentified the search text.")
            
            # Perform the replacement (only first occurrence to be safe)
            new_content = file_content.replace(search_text, replace_text, 1)
            
            # Verify change was made
            if new_content == file_content:
                raise ValueError(f"No changes were made. SEARCH: '{search_text}' REPLACE: '{replace_text}'")
            
            return new_content, description
            
        except Exception as e:
            logger.error("Smart edit failed: %s", e)
            raise
    
    def generate_branch_name(self, action: str, file_name: str, topic: str, user_query: str = "") -> str:
        """
        Generate a meaningful, intent-based branch name using AI.
        
        Args:
            action: Action type (create, update, delete)
            file_name: Name of the file
            topic: Topic/description
            user_query: Original user query for better context
        
        Returns:
            Git branch name based on user intent (e.g., "docs/llm-explanation-guide")
        """
        prompt = f"""You are a git expert. Analyze the user's intent and generate a perfect branch name.

User's Request: "{user_query if user_query else f'{action} {file_name} about {topic}'}"
File: {file_name}
Topic: {topic}

Generate a branch name that:
1. Clearly describes WHAT the user wants to achieve (not generic names)
2. Uses format: prefix/meaningful_description
3. Prefix based on intent:
   - docs/ for documentation, guides, explanations
   - feature/ for new functionality, code, features  
   - fix/ for corrections, bug fixes
   - update/ for modifications to existing content
4. Description should capture the ESSENCE of what's being done (e.g., "llm_basics_guide", "api_documentation", "python_tutorial")
5. NO timestamps, NO random numbers
6. Keep it under 40 characters total
7. Use lowercase and underscores only (NOT hyphens)

Think about what the user really wants, then output ONLY the branch name:"""

        try:
            response = self.client.post(
                f"{self.cortex_base}/model/ask/{self.model_name}",
                data={"q": prompt}
            )
            response.raise_for_status()
            branch_name = response.json().get("message", "").strip()
            
            # Clean up the branch name
            branch_name = branch_name.replace('"', '').replace("'", "").strip()
            # Remove any explanatory text, keep only the branch name
            if '\n' in branch_name:
                branch_name = branch_name.split('\n')[0]
            # Replace hyphens with underscores, remove invalid chars
            branch_name = branch_name.lower().replace('-', '_')
            branch_name = re.sub(r'[^a-z0-9\_\/]', '_', branch_name)
            branch_name = re.sub(r'_+', '_', branch_name).strip('_')
            
            # Ensure it has a prefix
            if '/' not in branch_name:
                prefix = "docs" if action == "create" else "update"
                branch_name = f"{prefix}/{branch_name}"
            
            return branch_name
            
        except Exception as e:
            logger.warning("AI branch generation failed, using fallback: %s", e)
            # Fallback - extract key words from topic
            prefix = "docs" if action == "create" else "update"
            # Extract meaningful words from topic
            words = re.findall(r'[a-zA-Z]+', topic.lower())[:3]
            meaningful_name = '_'.join(words) if words else file_name.rsplit(".", 1)[0]
            return f"{prefix}/{meaningful_name[:30]}"
    
    def generate_commit_message(self, action: str, file_name: str, topic: str, user_query: str = "") -> str:
        """
        Generate a meaningful commit message that reflects user intent.
        
        Args:
            action: Action type (create, update, delete)
            file_name: Name of the file
            topic: Topic/description of changes
            user_query: Original user query for better context
        
        Returns:
            Commit message that captures what the user wanted to do
        """
        prompt = f"""You are a git expert. Create a commit message that perfectly describes what the user wanted.

User's Request: "{user_query if user_query else f'{action} {file_name} about {topic}'}"
File: {file_name}
Topic: {topic}

Generate a commit message that:
1. Captures the USER'S INTENT, not just "add file" or "update file"
2. Uses conventional commit format: type(scope): description
3. Types:
   - docs: for documentation, guides, explanations
   - feat: for new features, functionality
   - fix: for corrections
   - chore: for maintenance
4. The description should explain WHAT was done in human terms
5. Use imperative mood ("add guide" not "added guide")
6. Be specific! "add LLM basics documentation" is better than "add file"
7. Under 60 characters

Examples of GOOD commit messages:
- docs: add comprehensive LLM explanation guide
- feat: create REST API documentation
- docs: add machine learning basics tutorial

Output ONLY the commit message:"""

        try:
            response = self.client.post(
                f"{self.cortex_base}/model/ask/{self.model_name}",
                data={"q": prompt}
            )
            response.raise_for_status()
            commit_msg = response.json().get("message", "").strip()
            
            # Clean up
            commit_msg = commit_msg.replace('"', '').replace("'", "").strip()
            if '\n' in commit_msg:
                commit_msg = commit_msg.split('\n')[0]
            
            # Ensure it's not too long
            if len(commit_msg) > 72:
                commit_msg = commit_msg[:69] + "..."
            
            logger.info(f"Generated commit message: {commit_msg}")
            return commit_msg
            
        except Exception as e:
            logger.warning(f"AI commit generation failed, using fallback: {e}")
            # Fallback - make it meaningful
            action_prefix = {"create": "docs", "update": "docs", "delete": "chore"}
            prefix = action_prefix.get(action, "chore")
            # Extract key concept from topic
            short_topic = topic[:35] if len(topic) <= 35 else topic[:32] + "..."
            return f"{prefix}: add {short_topic}"
    
    def generate_pr_title(self, action: str, file_name: str, topic: str, user_query: str = "") -> str:
        """
        Generate a clear PR title that reflects user's intent.
        
        Args:
            action: Action type
            file_name: Name of the file
            topic: Topic/description
            user_query: Original user query for better context
        
        Returns:
            PR title that clearly communicates the purpose
        """
        prompt = f"""Create a GitHub Pull Request title that clearly explains this change.

User's Request: "{user_query if user_query else f'{action} {file_name} about {topic}'}"
File: {file_name}
Topic: {topic}

Generate a PR title that:
1. Starts with a relevant emoji:
   - 📚 for documentation/guides
   - ✨ for new features
   - 📝 for content updates
   - 🔧 for fixes/improvements
2. Clearly states WHAT is being added/changed (from user's perspective)
3. Is professional and easy to understand
4. Under 60 characters
5. Uses Title Case

Examples of GOOD PR titles:
- 📚 Add Comprehensive LLM Explanation Guide
- ✨ Create REST API Documentation
- 📝 Add Machine Learning Basics Tutorial

Output ONLY the PR title:"""

        try:
            response = self.client.post(
                f"{self.cortex_base}/model/ask/{self.model_name}",
                data={"q": prompt}
            )
            response.raise_for_status()
            pr_title = response.json().get("message", "").strip()
            
            # Clean up
            pr_title = pr_title.replace('"', '').replace("'", "").strip()
            if '\n' in pr_title:
                pr_title = pr_title.split('\n')[0]
            
            # Ensure reasonable length
            if len(pr_title) > 80:
                pr_title = pr_title[:77] + "..."
            
            logger.info(f"Generated PR title: {pr_title}")
            return pr_title
            
        except Exception as e:
            logger.warning(f"AI PR title generation failed, using fallback: {e}")
            emoji = "📚" if action == "create" else "📝"
            # Create meaningful title from topic
            topic_title = topic.title()[:40] if len(topic) <= 40 else topic[:37].title() + "..."
            return f"{emoji} Add {topic_title}"
    
    def generate_pr_description(
        self,
        action: str,
        file_name: str,
        topic: str,
        content_preview: str = "",
        user_query: str = ""
    ) -> str:
        """
        Generate a comprehensive PR description using AI based on user intent.
        
        Args:
            action: Action type
            file_name: Name of the file
            topic: Topic/description
            content_preview: Preview of content (optional)
            user_query: Original user query for context
        
        Returns:
            PR description in Markdown format
        """
        preview = content_preview[:300] + "..." if len(content_preview) > 300 else content_preview
        
        prompt = f"""Create a professional GitHub Pull Request description.

User's Original Request: "{user_query if user_query else f'{action} {file_name} about {topic}'}"
File: {file_name}
Topic: {topic}

Write a PR description that:
1. Explains WHY this change was made (based on what user wanted)
2. Describes WHAT was added/changed
3. Highlights the VALUE this brings

Structure:
- Brief summary (2-3 sentences explaining the purpose)
- What's included (bullet points)
- Impact/benefit (1 sentence)

Keep it professional, concise, and human-readable.
Use markdown formatting.
Output ONLY the description:"""

        try:
            response = self.client.post(
                f"{self.cortex_base}/model/ask/{self.model_name}",
                data={"q": prompt}
            )
            response.raise_for_status()
            ai_description = response.json().get("message", "").strip()
            
            # Combine AI description with metadata
            timestamp = datetime.now().isoformat()
            
            full_description = f"""{ai_description}

---

## 📄 File Details
| Property | Value |
|----------|-------|
| File | `{file_name}` |
| Action | {action.upper()} |
| Generated | {timestamp} |

## 📋 Content Preview
```
{content_preview[:500]}{'...' if len(content_preview) > 500 else ''}
```

---
*🤖 This PR was automatically created by the AI File Assistant.*
"""
            logger.info("Generated PR description with AI")
            return full_description
            
        except Exception as e:
            logger.warning(f"AI PR description generation failed, using fallback: {e}")
            # Fallback
            timestamp = datetime.now().isoformat()
            preview_text = content_preview[:500] + "..." if len(content_preview) > 500 else content_preview
            
            return f"""## 📋 Summary
This PR {action}s the file `{file_name}`.

## 🎯 Changes
- **Action:** {action.upper()} file
- **Topic:** {topic}

## 📄 Content Preview
```
{preview_text}
```

## 🤖 Generated By
- AI File Assistant
- Timestamp: {timestamp}

---
*This PR was automatically created using the AI File Assistant.*
"""


def get_file_extension(file_name: str) -> str:
    """Extract file extension from filename."""
    if "." in file_name:
        return file_name.rsplit(".", 1)[-1].lower()
    return "txt"


def read_file(repo_path: str, file_name: str) -> Tuple[bool, str]:
    """
    Read content from an existing file.
    
    Args:
        repo_path: Path to repository
        file_name: Name of file to read
    
    Returns:
        Tuple of (success, content_or_error)
    """
    file_path = os.path.join(repo_path, file_name)
    
    if not os.path.exists(file_path):
        return False, f"File not found: {file_name}"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        logger.info(f"📖 Read file: {file_name} ({len(content)} chars)")
        return True, content
        
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        return False, str(e)


def edit_file(repo_path: str, file_name: str, new_content: str) -> Tuple[bool, str]:
    """
    Edit a file by replacing its entire content (for smart edits).
    
    Args:
        repo_path: Path to repository
        file_name: Name of file to edit
        new_content: The new complete content
    
    Returns:
        Tuple of (success, message)
    """
    file_path = os.path.join(repo_path, file_name)
    
    if not os.path.exists(file_path):
        return False, f"File not found: {file_name}"
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        logger.info(f"✏️ Edited file: {file_name}")
        return True, file_path
        
    except Exception as e:
        logger.error(f"Failed to edit file: {e}")
        return False, str(e)


def create_file(repo_path: str, file_name: str, content: str) -> Tuple[bool, str]:
    """
    Create a new file with content.
    
    Args:
        repo_path: Path to repository
        file_name: Name of file to create
        content: Content to write
    
    Returns:
        Tuple of (success, message)
    """
    file_path = os.path.join(repo_path, file_name)
    
    # Check if file already exists
    if os.path.exists(file_path):
        return False, f"File already exists: {file_name}"
    
    try:
        # Create directories if needed
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"✅ Created file: {file_name}")
        return True, file_path
        
    except Exception as e:
        logger.error(f"Failed to create file: {e}")
        return False, str(e)


def update_file(
    repo_path: str,
    file_name: str,
    new_content: str,
    update_type: str = "append"
) -> Tuple[bool, str]:
    """
    Update an existing file.
    
    Args:
        repo_path: Path to repository
        file_name: Name of file to update
        new_content: Content to add
        update_type: How to update (append, prepend, replace)
    
    Returns:
        Tuple of (success, message)
    """
    file_path = os.path.join(repo_path, file_name)
    
    if not os.path.exists(file_path):
        return False, f"File not found: {file_name}"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
        
        if update_type == "append":
            final_content = existing_content + "\n\n" + new_content
        elif update_type == "prepend":
            final_content = new_content + "\n\n" + existing_content
        else:  # replace
            final_content = new_content
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        
        logger.info(f"✅ Updated file: {file_name} ({update_type})")
        return True, file_path
        
    except Exception as e:
        logger.error(f"Failed to update file: {e}")
        return False, str(e)
