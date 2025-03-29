"""IMAP client implementation."""

import email
import logging
import re
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
        self.count_cache: Dict[str, Dict[str, Tuple[int, datetime]]] = {}  # Cache for message counts
        self.current_folder = None  # Store the currently selected folder
        self.folder_message_counts = {}  # Cache for folder message counts
    
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
        """Ensure that we are connected to the IMAP server.
        
        Raises:
            ConnectionError: If connection fails
        """
        if not self.connected:
            self.connect()
    
    def get_capabilities(self) -> List[str]:
        """Get IMAP server capabilities.
        
        Returns:
            List of server capabilities
            
        Raises:
            ConnectionError: If not connected and connection fails
        """
        self.ensure_connected()
        raw_capabilities = self.client.capabilities()
        
        # Convert byte strings to regular strings and normalize case
        capabilities = []
        for cap in raw_capabilities:
            if isinstance(cap, bytes):
                cap = cap.decode('utf-8')
            capabilities.append(cap.upper())
        
        return capabilities
    
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
    
    def _is_folder_allowed(self, folder: str) -> bool:
        """Check if a folder is allowed.
        
        Args:
            folder: Folder to check
            
        Returns:
            True if folder is allowed, False otherwise
        """
        # If no allowed_folders specified, all folders are allowed
        if self.allowed_folders is None:
            return True
        
        # If allowed_folders is specified, check if folder is in it
        return folder in self.allowed_folders
    
    def select_folder(self, folder: str, readonly: bool = False) -> Dict:
        """Select folder on IMAP server.
        
        Args:
            folder: Folder to select
            readonly: If True, select folder in read-only mode
        
        Returns:
            Dictionary with folder information
        
        Raises:
            ValueError: If folder is not allowed
            ConnectionError: If connection error occurs
        """
        # Make sure the folder is allowed
        if not self._is_folder_allowed(folder):
            raise ValueError(f"Folder '{folder}' is not allowed")
        
        self.ensure_connected()
        
        try:
            result = self.client.select_folder(folder, readonly=readonly)
            self.current_folder = folder
            logger.debug(f"Selected folder '{folder}'")
            return result
        except imapclient.IMAPClient.Error as e:
            logger.error(f"Error selecting folder {folder}: {e}")
            raise ConnectionError(f"Failed to select folder {folder}: {e}")
    
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
        self.select_folder(folder, readonly=True)
        
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
        self.select_folder(folder, readonly=True)
        
        # Fetch message data with BODY.PEEK[] to get all parts including headers
        # Using BODY.PEEK[] instead of RFC822 to avoid setting the \Seen flag
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
        self.select_folder(folder, readonly=True)
        
        # Apply limit if specified
        if limit is not None and limit > 0:
            uids = uids[:limit]
            
        # Fetch message data
        if not uids:
            return {}
            
        # Use BODY.PEEK[] to get full message including all parts and headers
        result = self.client.fetch(uids, ["BODY.PEEK[]", "FLAGS"])
        
        # Parse emails
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
        
    def fetch_thread(self, uid: int, folder: str = "INBOX") -> List[Email]:
        """Fetch all emails in a thread.
        
        This method retrieves the initial email identified by the UID, and then
        searches for all related emails that belong to the same thread using 
        Message-ID, In-Reply-To, References headers, and Subject matching as a fallback.
        
        Args:
            uid: UID of any email in the thread
            folder: Folder to fetch from
            
        Returns:
            List of Email objects in the thread, sorted chronologically
            
        Raises:
            ConnectionError: If not connected and connection fails
            ValueError: If the initial email cannot be found
        """
        self.ensure_connected()
        self.select_folder(folder, readonly=True)
        
        # Fetch the initial email
        initial_email = self.fetch_email(uid, folder)
        if not initial_email:
            raise ValueError(f"Initial email with UID {uid} not found in folder {folder}")
        
        # Get thread identifiers from the initial email
        message_id = initial_email.headers.get("Message-ID", "")
        subject = initial_email.subject
        
        # Strip "Re:", "Fwd:", etc. from the subject for better matching
        clean_subject = re.sub(r"^(?:Re|Fwd|Fw|FWD|RE|FW):\s*", "", subject, flags=re.IGNORECASE)
        
        # Set to store all UIDs that belong to the thread
        thread_uids = {uid}
        
        # Search for emails with this Message-ID in the References or In-Reply-To headers
        if message_id:
            # Look for emails that reference this message ID
            references_query = f'HEADER References "{message_id}"'
            try:
                references_results = self.search(references_query, folder)
                thread_uids.update(references_results)
            except Exception as e:
                logger.warning(f"Error searching for References: {e}")
            
            # Look for direct replies to this message
            inreplyto_query = f'HEADER In-Reply-To "{message_id}"'
            try:
                inreplyto_results = self.search(inreplyto_query, folder)
                thread_uids.update(inreplyto_results)
            except Exception as e:
                logger.warning(f"Error searching for In-Reply-To: {e}")
                
            # If the initial email has References or In-Reply-To, fetch those messages too
            initial_references = initial_email.headers.get("References", "")
            initial_inreplyto = initial_email.headers.get("In-Reply-To", "")
            
            # Extract all message IDs from the References header
            if initial_references:
                for ref_id in re.findall(r'<[^>]+>', initial_references):
                    query = f'HEADER Message-ID "{ref_id}"'
                    try:
                        results = self.search(query, folder)
                        thread_uids.update(results)
                    except Exception as e:
                        logger.warning(f"Error searching for Referenced message {ref_id}: {e}")
            
            # Look for the message that this is a reply to
            if initial_inreplyto:
                query = f'HEADER Message-ID "{initial_inreplyto}"'
                try:
                    results = self.search(query, folder)
                    thread_uids.update(results)
                except Exception as e:
                    logger.warning(f"Error searching for In-Reply-To message: {e}")
        
        # If we still have only the initial email or a small thread, try subject-based matching
        if len(thread_uids) <= 2 and clean_subject:
            # Look for emails with the same or related subject (Re: Subject)
            # This is a fallback for email clients that don't properly use References/In-Reply-To
            subject_query = f'SUBJECT "{clean_subject}"'
            try:
                subject_results = self.search(subject_query, folder)
                
                # Filter out emails that are unlikely to be part of the thread
                # For example, avoid including all emails with a common subject like "Hello"
                if len(subject_results) < 20:  # Set a reasonable limit
                    thread_uids.update(subject_results)
                else:
                    # If there are too many results, try a more strict approach
                    # Look for exact subject match or common Re: pattern
                    strict_matches = []
                    strict_subjects = [
                        clean_subject,
                        f"Re: {clean_subject}",
                        f"RE: {clean_subject}",
                        f"Fwd: {clean_subject}",
                        f"FWD: {clean_subject}",
                        f"Fw: {clean_subject}",
                        f"FW: {clean_subject}"
                    ]
                    
                    # Fetch subjects for all candidate emails
                    candidate_emails = self.fetch_emails(subject_results, folder)
                    for candidate_uid, candidate_email in candidate_emails.items():
                        if candidate_email.subject in strict_subjects:
                            strict_matches.append(candidate_uid)
                    
                    thread_uids.update(strict_matches)
            except Exception as e:
                logger.warning(f"Error searching by subject: {e}")
        
        # Fetch all discovered thread emails
        thread_emails = self.fetch_emails(list(thread_uids), folder)
        
        # Sort emails by date (chronologically)
        sorted_emails = sorted(
            thread_emails.values(), 
            key=lambda e: e.date if e.date else datetime.min
        )
        
        return sorted_emails
    
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
    
    def get_message_count(self, folder: str, status: Optional[str] = None, refresh: bool = False) -> int:
        """
        Get message count in folder with optional filter by status.
        
        Args:
            folder: Folder name to get count from
            status: Optional filter - 'TOTAL', 'UNSEEN', or 'SEEN'
            refresh: Force refresh count from server
            
        Returns:
            Integer count of messages matching the criteria
            
        Raises:
            ConnectionError: If not connected and connection fails
            ValueError: If folder is not allowed
        """
        # Normalize status
        if status is None:
            status = "TOTAL"
        status = status.upper()
        
        # Check if folder is allowed
        if self.allowed_folders and folder not in self.allowed_folders:
            raise ValueError(f"Folder '{folder}' is not allowed. Allowed folders: {self.allowed_folders}")
        
        # Check cache unless refresh is requested
        if not refresh and folder in self.folder_message_counts:
            cached_info = self.folder_message_counts[folder]
            cached_time = cached_info["time"]
            cached_count = cached_info.get(status, 0)
            current_time = datetime.now()
            
            # Use cache if it's less than 5 seconds old
            if (current_time - cached_time).total_seconds() < 5:
                logger.debug(f"Using cached message count for {folder} with status {status}: {cached_count}")
                return cached_count
        
        # Ensure connection
        self.ensure_connected()
        
        # Get folder status
        folder_status = self.get_folder_status(folder)
        
        # Get count based on status
        if status == "TOTAL":
            # Get total message count from folder status
            count = folder_status.get(b"MESSAGES", 0)
        elif status == "UNSEEN":
            # Get unread message count from folder status
            count = folder_status.get(b"UNSEEN", 0)
        elif status == "SEEN":
            # Calculate read count as total - unread
            total_count = folder_status.get(b"MESSAGES", 0)
            unread_count = folder_status.get(b"UNSEEN", 0)
            count = max(0, total_count - unread_count)  # Ensure it's never negative
        else:
            raise ValueError(f"Invalid status: {status}. Must be one of: TOTAL, UNSEEN, SEEN")
            
        # Update cache
        if folder not in self.folder_message_counts:
            self.folder_message_counts[folder] = {}
        self.folder_message_counts[folder]["time"] = datetime.now()
        self.folder_message_counts[folder][status] = count
        
        logger.debug(f"Message count for {folder} with status {status}: {count}")
        
        return count

    def get_total_count(self, folder: str, refresh: bool = False) -> int:
        """
        Get total message count in folder.
        
        Args:
            folder: Folder name to get count from
            refresh: Force refresh count from server
            
        Returns:
            Integer count of total messages
            
        Raises:
            ConnectionError: If not connected and connection fails
            ValueError: If folder is not allowed
        """
        return self.get_message_count(folder, status="TOTAL", refresh=refresh)
    
    def get_unread_count(self, folder: str, refresh: bool = False) -> int:
        """
        Get count of unread messages in folder.
        
        Args:
            folder: Folder name to get count from
            refresh: Force refresh count from server
            
        Returns:
            Integer count of unread messages
            
        Raises:
            ConnectionError: If not connected and connection fails
            ValueError: If folder is not allowed
        """
        return self.get_message_count(folder, status="UNSEEN", refresh=refresh)
    
    def get_read_count(self, folder: str, refresh: bool = False) -> int:
        """
        Get count of read messages in folder.
        
        Args:
            folder: Folder name to get count from
            refresh: Force refresh count from server
            
        Returns:
            Integer count of read messages
            
        Raises:
            ConnectionError: If not connected and connection fails
            ValueError: If folder is not allowed
        """
        # Ensure we get a consistent count by using a single folder status check
        self.ensure_connected()
        folder_status = self.get_folder_status(folder)
        total = folder_status.get(b"MESSAGES", 0)
        unread = folder_status.get(b"UNSEEN", 0)
        read = max(0, total - unread)  # Ensure it's never negative
        
        # Cache the read count
        if folder not in self.folder_message_counts:
            self.folder_message_counts[folder] = {}
        self.folder_message_counts[folder]["time"] = datetime.now()
        self.folder_message_counts[folder]["SEEN"] = read
        
        return read
    
    def get_folder_status(self, folder: str) -> Dict[str, int]:
        """Get status information for a folder.

        Args:
            folder: Folder name

        Returns:
            Dictionary with status information (MESSAGES, RECENT, UNSEEN, etc.)
        """
        self.ensure_connected()
        
        try:
            # STATUS command returns information about the folder without selecting it
            status = self.client.folder_status(folder, ["MESSAGES", "RECENT", "UNSEEN", "UIDNEXT", "UIDVALIDITY"])
            logger.debug(f"Folder status for {folder}: {status}")
            
            # Add EXISTS key for compatibility with tests that expect it
            status[b"EXISTS"] = status.get(b"MESSAGES", 0)
            
            return status
        except Exception as e:
            logger.error(f"Failed to get status for folder {folder}: {e}")
            raise ValueError(f"Failed to get status for folder {folder}: {e}")
    
    def _sort_results(
        self, 
        emails: Dict[int, Email], 
        sort_by: str, 
        sort_order: str
    ) -> Dict[int, Email]:
        """Sort email results by specified field.
        
        Args:
            emails: Dictionary of UIDs to Email objects
            sort_by: Field to sort by ('date', 'size', 'from', 'subject')
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Sorted dictionary of UIDs to Email objects
            
        Raises:
            ValueError: If sort_by or sort_order is invalid
        """
        valid_sort_fields = {"date", "size", "from", "subject"}
        valid_sort_orders = {"asc", "desc"}
        
        if sort_by not in valid_sort_fields:
            raise ValueError(f"Invalid sort_by: {sort_by}. Must be one of {valid_sort_fields}")
        
        if sort_order not in valid_sort_orders:
            raise ValueError(f"Invalid sort_order: {sort_order}. Must be one of {valid_sort_orders}")
        
        # Handle special case for 'from' which is a reserved keyword
        if sort_by == "from":
            attr_name = "from_"
        else:
            attr_name = sort_by
            
        # Sort the emails based on the specified attribute
        reverse = sort_order == "desc"
        sorted_emails = dict(
            sorted(
                emails.items(),
                key=lambda item: getattr(item[1], attr_name) or "",  # Use empty string if None
                reverse=reverse
            )
        )
        
        return sorted_emails
    
    def _paginate_results(
        self, 
        emails: Dict[int, Email], 
        offset: int, 
        limit: Optional[int]
    ) -> Dict[int, Email]:
        """Paginate results with offset and limit.
        
        Args:
            emails: Dictionary of UIDs to Email objects
            offset: Number of items to skip
            limit: Maximum number of items to return (None for all)
            
        Returns:
            Paginated dictionary of UIDs to Email objects
            
        Raises:
            ValueError: If offset is negative or limit is zero
        """
        if offset < 0:
            raise ValueError("Offset cannot be negative")
        
        if limit is not None and limit <= 0:
            raise ValueError("Limit must be positive")
            
        # Get list of keys (UIDs)
        keys = list(emails.keys())
        
        # Apply pagination
        start = offset
        end = None if limit is None else offset + limit
        
        # Slice the keys and create a new dictionary
        paginated_keys = keys[start:end]
        paginated_emails = {k: emails[k] for k in paginated_keys}
        
        return paginated_emails
    
    def get_unread_messages(
        self, 
        folder: str = "INBOX", 
        limit: Optional[int] = 10,
        offset: int = 0,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> Dict[int, Email]:
        """Get unread messages from folder with pagination.
        
        Args:
            folder: Folder to fetch from
            limit: Maximum number of messages to retrieve (None for all)
            offset: Number of messages to skip
            sort_by: Field to sort by ('date', 'size', 'from', 'subject')
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Dictionary mapping UIDs to Email objects
            
        Raises:
            ConnectionError: If not connected and connection fails
            ValueError: If folder is not allowed or parameters are invalid
        """
        # Validate parameters
        if offset < 0:
            raise ValueError("Offset cannot be negative")
        
        if limit is not None and limit <= 0:
            raise ValueError("Limit must be positive")
            
        valid_sort_fields = {"date", "size", "from", "subject"}
        if sort_by not in valid_sort_fields:
            raise ValueError(f"Invalid sort_by: {sort_by}. Must be one of {valid_sort_fields}")
            
        valid_sort_orders = {"asc", "desc"}
        if sort_order not in valid_sort_orders:
            raise ValueError(f"Invalid sort_order: {sort_order}. Must be one of {valid_sort_orders}")
        
        # Ensure connection and select folder
        self.ensure_connected()
        self.select_folder(folder)
        
        # Check if server supports SORT capability
        use_server_sort = False
        capabilities = self.get_capabilities()
        if "SORT" in capabilities:
            use_server_sort = True
            logger.debug("Using server-side sorting")
        else:
            logger.debug("Server does not support SORT, using client-side sorting")
        
        # Search for unread messages
        unread_uids = self.search("UNSEEN", folder=folder)
        
        if not unread_uids:
            return {}
        
        # Fetch all unread messages
        emails = self.fetch_emails(unread_uids, folder=folder)
        
        # Sort the results
        sorted_emails = self._sort_results(emails, sort_by, sort_order)
        
        # Apply pagination
        paginated_emails = self._paginate_results(sorted_emails, offset, limit)
        
        return paginated_emails

    def _get_drafts_folder(self) -> str:
        """Get the name of the appropriate drafts folder for the current server.
        
        This method intelligently determines the most appropriate drafts folder
        based on the server type and available folders. It handles different server
        configurations:
        
        1. Gmail: Uses '[Gmail]/Drafts' or similar Gmail-specific folder
        2. Standard IMAP: Uses 'Drafts' folder
        3. Fallback: If no drafts folder is found, returns 'Drafts' as a default
        
        The method checks server capabilities to identify Gmail servers (which use
        the X-GM-EXT capability), then looks for appropriate folders in the folder list.
        
        Returns:
            str: The name of the drafts folder to use
        """
        self.ensure_connected()
        
        # Get list of folders
        folders = self.list_folders()
        
        # Check capabilities to see if this is Gmail
        capabilities = self.get_capabilities()
        is_gmail = any(cap.startswith('X-GM-EXT') for cap in capabilities)
        
        # Look for Gmail's drafts folder
        if is_gmail:
            gmail_drafts = '[Gmail]/Drafts'
            if gmail_drafts in folders:
                return gmail_drafts
            
            # Some Gmail accounts might have different folder structure
            for folder in folders:
                if '/Drafts' in folder:
                    return folder
        
        # Look for standard drafts folder
        if 'Drafts' in folders:
            return 'Drafts'
        
        # If no drafts folder found, create one or use a fallback
        # In real implementation, we might want to create a Drafts folder here
        logger.warning("No drafts folder found, using 'Drafts' as fallback")
        return 'Drafts'
    
    def save_draft_mime(self, mime_message: Message) -> Optional[int]:
        """Save a MIME message as a draft in the drafts folder.
        
        This method saves an email.message.Message object as a draft message
        in the user's drafts folder. It:
        
        1. Automatically determines the appropriate drafts folder
        2. Appends the message with the \\Draft flag
        3. Extracts and returns the UID of the newly created draft message
        
        The method parses the server's response to extract the UID of the saved
        draft message, which can be used for further operations on the draft.
        
        Example:
            ```python
            # Create a MIME message
            from email.mime.text import MIMEText
            msg = MIMEText("Draft message content")
            msg['Subject'] = "Draft Subject"
            msg['To'] = "recipient@example.com"
            msg['From'] = "sender@example.com"
            
            # Save as draft
            draft_uid = imap_client.save_draft_mime(msg)
            
            if draft_uid:
                print(f"Draft saved with UID: {draft_uid}")
            else:
                print("Failed to save draft")
            ```
        
        Args:
            mime_message: The email.message.Message object to save as a draft
            
        Returns:
            Optional[int]: The UID of the saved draft message if successful,
                          None if the message couldn't be saved or if the UID
                          couldn't be determined from the server response
        """
        if not self.connected:
            logger.error("Not connected to IMAP server")
            return None
        
        try:
            # Get the drafts folder
            drafts_folder = self._get_drafts_folder()
            
            # Convert the message to bytes
            message_bytes = mime_message.as_bytes()
            
            # Append the message to the drafts folder with the \Draft flag
            result = self.client.append(drafts_folder, message_bytes, ["\\Draft"])
            
            # Try to extract the UID from the response
            # The APPENDUID response format is: [APPENDUID <UIDVALIDITY> <UID>]
            # For example: b'[APPENDUID 1234567890 123]'
            uid = None
            if result:
                result_str = str(result)
                match = re.search(r'APPENDUID \d+ (\d+)', result_str, re.IGNORECASE)
                if match:
                    uid = int(match.group(1))
            
            if uid:
                logger.info(f"Draft saved to {drafts_folder} with UID {uid}")
                return uid
            else:
                logger.warning("Draft saved but couldn't determine UID")
                return None
                
        except Exception as e:
            logger.error(f"Error saving draft: {e}")
            return None
