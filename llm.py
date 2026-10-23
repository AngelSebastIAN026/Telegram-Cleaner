import asyncio
import os

from google import genai
from google.genai import types

from telethon.tl.functions.channels import LeaveChannelRequest


class GeminiLLM:

    def __init__(
        self,
        telegram_client,
        database,
    ):
        self.client_telegram = telegram_client
        self.database = database

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash-lite",
        )

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is missing from .env"
            )

        self.client = genai.Client(
            api_key=api_key
        )

    

    def get_tools(self):

        store_pending_declaration = (
            types.FunctionDeclaration(
                name="store_pending_invite",
                description=(
                    "Store a private Telegram invite that "
                    "requires admin approval in the pending "
                    "invite database."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "invite_hash": {
                            "type": "string",
                            "description": (
                                "Telegram private invite hash."
                            ),
                        },
                        "title": {
                            "type": "string",
                            "description": (
                                "Title of the Telegram channel."
                            ),
                        },
                    },
                    "required": [
                        "invite_hash",
                        "title",
                    ],
                },
            )
        )

        leave_channel_declaration = (
            types.FunctionDeclaration(
                name="leave_channel",
                description=(
                    "Leave a Telegram channel after the "
                    "channel has become active from a previously "
                    "approved private invite."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "integer",
                            "description": (
                                "Telegram channel ID."
                            ),
                        },
                        "invite_hash": {
                            "type": "string",
                            "description": (
                                "The private invite hash associated "
                                "with the channel."
                            ),
                        },
                        "title": {
                            "type": "string",
                            "description": (
                                "Channel title."
                            ),
                        },
                    },
                    "required": [
                        "channel_id",
                        "invite_hash",
                        "title",
                    ],
                },
            )
        )

        return types.Tool(
            function_declarations=[
                store_pending_declaration,
                leave_channel_declaration,
            ]
        )

    

    async def execute_tool(
        self,
        name,
        arguments,
    ):

        print()
        print("Executing Python tool...")
        print(f"Tool: {name}")
        print(f"Arguments: {arguments}")

        
        if name == "store_pending_invite":

            invite_hash = str(
                arguments.get("invite_hash") or ""
            ).strip()

            title = str(
                arguments.get("title") or ""
            ).strip()

            if not invite_hash:
                return {
                    "status": "error",
                    "message": (
                        "Invite hash was not provided."
                    ),
                }

            if not title:
                return {
                    "status": "error",
                    "message": (
                        "Channel title was not provided."
                    ),
                }

            existing = (
                self.database.get_pending_invite(
                    invite_hash
                )
            )

            if existing is not None:

                print(
                    "Invite is already stored."
                )

                return {
                    "status": "already_exists",
                    "invite_hash": invite_hash,
                    "title": title,
                }

            from datetime import datetime

            now = datetime.now().isoformat()

            self.database.add_pending_invite(
                invite_hash=invite_hash,
                title=title,
                created_at=now,
                updated_at=now,
            )

            print()
            print(
                "Agent action completed:"
            )
            print(
                f"Stored pending invite: {title}"
            )

            return {
                "status": "stored",
                "invite_hash": invite_hash,
                "title": title,
                "state": "pending",
            }

        

        if name == "leave_channel":

            channel_id = arguments.get(
                "channel_id"
            )

            invite_hash = str(
                arguments.get("invite_hash") or ""
            ).strip()

            title = str(
                arguments.get("title") or ""
            ).strip()

            if not channel_id:
                return {
                    "status": "error",
                    "message": (
                        "Channel ID was not provided."
                    ),
                }

            if not invite_hash:
                return {
                    "status": "error",
                    "message": (
                        "Invite hash was not provided."
                    ),
                }

            if not title:
                return {
                    "status": "error",
                    "message": (
                        "Channel title was not provided."
                    ),
                }

            try:

                channel = (
                    await self.client_telegram.get_entity(
                        int(channel_id)
                    )
                )

                print()
                print(
                    "Agent action:"
                )
                print(
                    f"Leaving channel: {title}"
                )

                await self.client_telegram(
                    LeaveChannelRequest(
                        channel
                    )
                )

                from datetime import datetime

                now = datetime.now().isoformat()

                existing_channel = (
                    self.database.get_channel(
                        int(channel_id)
                    )
                )

                if existing_channel is not None:

                    self.database.update_status(
                        channel_id=int(channel_id),
                        status="left",
                        updated_at=now,
                    )

                self.database.update_pending_invite_status(
                    invite_hash=invite_hash,
                    status="left",
                    updated_at=now,
                )

                print(
                    f"Agent left channel: {title}"
                )

                return {
                    "status": "left",
                    "channel_id": int(channel_id),
                    "title": title,
                    "invite_hash": invite_hash,
                }

            except Exception as error:

                print()
                print(
                    "Agent failed to leave channel:"
                )
                print(error)

                return {
                    "status": "error",
                    "channel_id": int(channel_id),
                    "title": title,
                    "message": str(error),
                }

        

        return {
            "status": "error",
            "message": (
                f"Unknown tool: {name}"
            ),
        }

    

    async def ask_with_tool(
        self,
        prompt,
    ):

        print()
        print("Calling Gemini...")
        print(
            f"Model: {self.model}"
        )

        tool_results = []

        try:

            tool = self.get_tools()

            config = types.GenerateContentConfig(
                tools=[tool],

                automatic_function_calling=(
                    types.AutomaticFunctionCallingConfig(
                        disable=True
                    )
                ),
            )

            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=prompt
                        )
                    ],
                )
            ]

            max_rounds = 5

            for round_number in range(
                max_rounds
            ):

                print()
                print(
                    f"Gemini round "
                    f"{round_number + 1}"
                )

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=contents,
                    config=config,
                )

                print()
                print(
                    "Gemini responded."
                )

                if not response.candidates:

                    return {
                        "type": "error",
                        "error": (
                            "Gemini returned "
                            "no candidates."
                        ),
                        "tool_results": tool_results,
                    }

                model_content = (
                    response
                    .candidates[0]
                    .content
                )

                function_calls = []

                for part in model_content.parts:

                    function_call = getattr(
                        part,
                        "function_call",
                        None,
                    )

                    if function_call:
                        function_calls.append(
                            function_call
                        )

                

                if not function_calls:

                    output_text = str(
                        getattr(
                            response,
                            "text",
                            ""
                        )
                        or ""
                    )

                    print()
                    print(
                        "Gemini produced "
                        "final response."
                    )

                    return {
                        "type": "text",
                        "text": output_text,
                        "tool_results": (
                            tool_results
                        ),
                    }

                

                contents.append(
                    model_content
                )

                

                for function_call in (
                    function_calls
                ):

                    name = getattr(
                        function_call,
                        "name",
                        None,
                    )

                    arguments = getattr(
                        function_call,
                        "args",
                        {},
                    )

                    if not isinstance(
                        arguments,
                        dict,
                    ):

                        try:
                            arguments = dict(
                                arguments
                            )

                        except Exception:
                            arguments = {}

                    print()
                    print(
                        "Gemini selected tool:"
                    )
                    print(
                        f"  Tool: {name}"
                    )
                    print(
                        f"  Arguments: "
                        f"{arguments}"
                    )

                    result = (
                        await self.execute_tool(
                            name,
                            arguments,
                        )
                    )

                    print()
                    print(
                        "Python tool result:"
                    )
                    print(result)

                    tool_results.append(
                        {
                            "tool_name": name,
                            "arguments": arguments,
                            "result": result,
                        }
                    )

                    

                    function_response = (
                        types.Part
                        .from_function_response(
                            name=name,
                            response={
                                "result": result
                            },
                        )
                    )

                    contents.append(
                        types.Content(
                            role="user",
                            parts=[
                                function_response
                            ],
                        )
                    )

            return {
                "type": "error",
                "error": (
                    "Gemini exceeded the maximum "
                    "number of tool rounds."
                ),
                "tool_results": tool_results,
            }

        except Exception as error:

            print()
            print("Gemini failed:")
            print(error)

            return {
                "type": "error",
                "error": str(error),
                "tool_results": tool_results,
            }

    

    async def ask(
        self,
        prompt,
    ):

        print()
        print("Calling Gemini...")
        print(
            f"Model: {self.model}"
        )

        try:

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt,
            )

            text = getattr(
                response,
                "text",
                ""
            )

            return str(
                text or ""
            )

        except Exception as error:

            print()
            print("Gemini failed:")
            print(error)

            return ""