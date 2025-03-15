"""IMAP client implementation."""

import email
import logging
from datetime import datetime, timedelta
from email.message import Message
from typing import Dict, List, Optional, Set, Tuple, Union

import imapclient
from imapclient.response_types import SearchIds

from imap_mcp.config import ImapConfig
from imap_mcp.models import Email
from imap_mcp.oauth2 import get_access_token, generate_oauth2_string

logger = logging.getLogger(__name__)


class ImapClient:
    """IMAP client for interacting with email servers."""
    
    def __init__(self, config: ImapConfig, allowed_folders: Optional[List[str]] = None):
        """Initialize IMAP client.
        
        Args:
            config: IMAP configuration
            allowed_folders: List of allowed folders (None means all folders)
        """
        self.config = config
        self.allowed_folders = set(allowed_folders) if allowed_folders else None
        self.client = None
        self.folder_cache: Dict[str, List[str]] = {}
        self.connected = False
    
    def connect(self) -> None:
        """Connect to IMAP server.
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.client = imapclient.IMAPClient(
                self.config.host, 
                port=self.config.port, 
                ssl=self.config.use_ssl,
            )
            
            # Use OAuth2 for Gmail if configured
            if self.config.requires_oauth2:
                logger.info(f"Using OAuth2 authentication for {self.config.host}")
                
                # Get fresh access token
                if not self.config.oauth2:
                    raise ValueError("OAuth2 configuration is required for Gmail")
                
                access_token, _ = get_access_token(self.config.oauth2)
                
                # Authenticate with XOAUTH2
                # Use the oauth_login method which properly formats the XOAUTH2 string
                self.client.oauth2_login(self.config.username, access_token)
            else:
                # Standard password authentication
                if not self.config.password:
                    raise ValueError("Password is required for authentication")
                    
                self.client.login(self.config.username, self.config.password)
                
            self.connected = True
            logger.info(f"Connected to IMAP server {self.config.host}")
        except Exception as e:
            self.connected = False
            logger.error(f"Failed to connect to IMAP server: {e}")
            raise ConnectionError(f"Failed to connect to IMAP server: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from IMAP server."""
        if self.client:
            try:
                self.client.logout()
            except Exception as e:
                logger.warning(f"Error during IMAP logout: {e}")
            finally:
                self.client = None
                self.connected = False
                logger.info("Disconnected from IMAP server")
    
    def ensure_connected(self) -> None:
        """Ensure connection is established.
        
        Raises:
            ConnectionError: If not connected and connection fails
        """
        if not self.connected or not self.client:
            self.connect()
    
    def list_folders(self, refresh: bool = False) -> List[str]:
        """List available folders.
        
        Args:
            refresh: Force refresh folder list cache
            
        Returns:
            List of folder names
            
        Raises:
            ConnectionError: If not connected and connection fails
        """
        self.ensure_connected()
        
        # Check cache first
        if not refresh and self.folder_cache:
            return list(self.folder_cache.keys())
        
        # Get folders from server
        folders = []
        for flags, delimiter, name in self.client.list_folders():
            if isinstance(name, bytes):
                # Convert bytes to string if necessary
                name = name.decode("utf-8")
            
            # Filter folders if allowed_folders is set
            if self.allowed_folders is not None and name not in self.allowed_folders:
                continue
            
            folders.append(name)
            self.folder_cache[name] = flags
        
        logger.debug(f"Listed {len(folders)} folders")
        return folders
    
    def select_folder(self, folder: str) -> Dict:
        """Select a folder.
        
        Args:
            folder: Folder name
            
        Returns:
            Folder information
            
        Raises:
            ConnectionError: If not connected and connection fails
            ValueError: If folder is not allowed
        """
        self.ensure_connected()
        
        # Check if folder is allowed
        if self.allowed_folders is not None and folder not in self.allowed_folders:
            raise ValueError(f"Folder '{folder}' is not allowed")
        
        # Select folder
        result = self.client.select_folder(folder)
        logger.debug(f"Selected folder {folder}")
        return result
    
    def search(
        self, 
        criteria: Union[str, List, Tuple],
        folder: str = "INBOX",
        charset: Optional[str] = None,
    ) -> List[int]:
        """Search for messages.
        
        Args:
            criteria: Search criteria
            folder: Folder to search in
            charset: Character set for search criteria
            
        Returns:
            List of message UIDs
            
        Raises:
            ConnectionError: If not connected and connection fails
        """
        self.ensure_connected()
        self.select_folder(folder)
        
        if isinstance(criteria, str):
            # Predefined criteria strings
            criteria_map = {
                "all": "ALL",
                "unseen": "UNSEEN",
                "seen": "SEEN",
                "answered": "ANSWERED",
                "unanswered": "UNANSWERED",
                "deleted": "DELETED",
                "undeleted": "UNDELETED",
                "flagged": "FLAGGED",
                "unflagged": "UNFLAGGED",
                "recent": "RECENT",
                "today": ["SINCE", datetime.now().date()],
                "yesterday": [
                    "SINCE", 
                    (datetime.now() - timedelta(days=1)).date(),
                    "BEFORE",
                    datetime.now().date(),
                ],
                "week": ["SINCE", (datetime.now() - timedelta(days=7)).date()],
                "month": ["SINCE", (datetime.now() - timedelta(days=30)).date()],
            }
            
            if criteria.lower() in criteria_map:
                criteria = criteria_map[criteria.lower()]
        
        results = self.client.search(criteria, charset=charset)
        logger.debug(f"Search returned {len(results)} results")
        return list(results)
    
    def fetch_email(self, uid: int, folder: str = "INBOX") -> Optional[Email]:
        """Fetch a single email by UID.
        
        Args:
            uid: Email UID
            folder: Folder to fetch from
            
        Returns:
            Email object or None if not found
            
        Raises:
            ConnectionError: If not connected and connection fails
        """
        self.ensure_connected()
        self.select_folder(folder)
        
        # Fetch message data
        result = self.client.fetch([uid], ["BODY.PEEK[]", "FLAGS"])
        
        if not result or uid not in result:
            logger.warning(f"Message with UID {uid} not found in folder {folder}")
            return None
        
        # Parse message
        message_data = result[uid]
        raw_message = message_data[b"BODY[]"]
        flags = message_data[b"FLAGS"]
        
        # Convert flags to strings
        str_flags = [
            f.decode("utf-8") if isinstance(f, bytes) else f 
            for f in flags
        ]
        
        # Parse email
        message = email.message_from_bytes(raw_message)
        email_obj = Email.from_message(message, uid=uid, folder=folder)
        email_obj.flags = str_flags
        
        return email_obj
    
    def fetch_emails(
        self, 
        uids: List[int], 
        folder: str = "INBOX",
        limit: Optional[int] = None,
    ) -> Dict[int, Email]:
        """Fetch multiple emails by UIDs.
        
        Args:
            uids: List of email UIDs
            folder: Folder to fetch from
            limit: Maximum number of emails to fetch
            
        Returns:
            Dictionary mapping UIDs to Email objects
            
        Raises:
            ConnectionError: If not connected and connection fails
        """
        self.ensure_connected()
        self.select_folder(folder)
        
        # Apply limit if specified
        if limit is not None and limit < len(uids):
            uids = uids[:limit]
        
        if not uids:
            return {}
        
        # Fetch message data
        result = self.client.fetch(uids, ["BODY.PEEK[]", "FLAGS"])
        emails = {}
        
        for uid, message_data in result.items():
            raw_message = message_data[b"BODY[]"]
            flags = message_data[b"FLAGS"]
            
            # Convert flags to strings
            str_flags = [
                f.decode("utf-8") if isinstance(f, bytes) else f 
                for f in flags
            ]
            
            # Parse email
            message = email.message_from_bytes(raw_message)
            email_obj = Email.from_message(message, uid=uid, folder=folder)
            email_obj.flags = str_flags
            emails[uid] = email_obj
        
        return emails
    
    def mark_email(
        self, 
        uid: int, 
        folder: str,
        flag: str, 
        value: bool = True,
    ) -> bool:
        """Mark email with flag.
        
        Args:
            uid: Email UID
            folder: Folder containing the email
            flag: Flag to set or remove
            value: True to set, False to remove
            
        Returns:
            True if successful
            
        Raises:
            ConnectionError: If not connected and connection fails
        """
        self.ensure_connected()
        self.select_folder(folder)
        
        try:
            if value:
                self.client.add_flags([uid], flag)
                logger.debug(f"Added flag {flag} to message {uid}")
            else:
                self.client.remove_flags([uid], flag)
                logger.debug(f"Removed flag {flag} from message {uid}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark email: {e}")
            return False
    
    def move_email(self, uid: int, source_folder: str, target_folder: str) -> bool:
        """Move email to another folder.
        
        Args:
            uid: Email UID
            source_folder: Source folder
            target_folder: Target folder
            
        Returns:
            True if successful
            
        Raises:
            ConnectionError: If not connected and connection fails
            ValueError: If folder is not allowed
        """
        self.ensure_connected()
        
        # Check if folders are allowed
        if self.allowed_folders is not None:
            if source_folder not in self.allowed_folders:
                raise ValueError(f"Source folder '{source_folder}' is not allowed")
            if target_folder not in self.allowed_folders:
                raise ValueError(f"Target folder '{target_folder}' is not allowed")
        
        # Select source folder
        self.select_folder(source_folder)
        
        try:
            # Move email (copy + delete)
            self.client.copy([uid], target_folder)
            self.client.add_flags([uid], r"\Deleted")
            self.client.expunge()
            logger.debug(f"Moved message {uid} from {source_folder} to {target_folder}")
            return True
        except Exception as e:
            logger.error(f"Failed to move email: {e}")
            return False
    
    def delete_email(self, uid: int, folder: str) -> bool:
        """Delete email.
        
        Args:
            uid: Email UID
            folder: Folder containing the email
            
        Returns:
            True if successful
            
        Raises:
            ConnectionError: If not connected and connection fails
        """
        self.ensure_connected()
        self.select_folder(folder)
        
        try:
            self.client.add_flags([uid], r"\Deleted")
            self.client.expunge()
            logger.debug(f"Deleted message {uid} from {folder}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete email: {e}")
            return False
