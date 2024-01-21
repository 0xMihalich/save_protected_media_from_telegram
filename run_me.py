from io     import BytesIO
from typing import Optional, Union

from telethon          import  TelegramClient
from telethon.events   import  NewMessage
from telethon.tl.types import (DocumentAttributeFilename,
                               MessageMediaPhoto,
                               MessageMediaDocument,
                               MessageMediaWebPage,
                               Channel,
                               User,)


api_id   : int            = 1234                # указать свой api_id
api_hash : str            = '01234567890abcdef' # указать свой api_hash
client   : TelegramClient = TelegramClient('anon',
                                           api_id,
                                           api_hash,
                                           system_version="4.16.30-vxCUSTOM",)

media_types = {
    "audio/ogg"  : "голосовое сообщение",
    "audio/mpeg" : "аудиофайл",
    "video/mp4"  : "видео",
}


def get_media_type(media: Union[MessageMediaPhoto, MessageMediaDocument,]) -> str:
    "определить тип медиаконтента"

    if isinstance(media, MessageMediaPhoto):
        return "фото"
    
    return media_types.get(media.document.mime_type, "документ")


def get_file_name(media: Union[MessageMediaPhoto, MessageMediaDocument,],
                  media_type: str,) -> str:
    "получение имени для файлоподобного объекта"

    if media_type == "фото":
        return "photo.jpg"
    elif media_type == "видео":
        return "video.mp4"
    elif media_type == "аудиофайл":
        return "music.mp3"
    elif media_type == "голосовое сообщение":
        return "voice.ogg"
    
    for attr in media.document.attributes:
        if isinstance(attr, DocumentAttributeFilename):
            return attr.file_name
    
    return "unknown.bin"


@client.on(NewMessage)
async def save_protected_media(message: NewMessage.Event) -> None:
    "автосохранение медиаконтента в избранное из защищенных групп"
    "и личных переписок/секретных чатов с самоуничтожающимся контентом"

    media: Optional[Union[MessageMediaPhoto,
                          MessageMediaDocument,
                          MessageMediaWebPage,]] = message.media
    
    if not media or isinstance(media, MessageMediaWebPage):
        return

    media_type : str                  = get_media_type(media)
    chat       : Union[Channel, User] = message.chat
    ttl_seconds: int                  = media.ttl_seconds
    protected  : bool                 = (chat.noforwards
                                         if not isinstance(chat, User)
                                         else False)

    if ttl_seconds:
        vanishing = ("сразу после просмотра" if ttl_seconds == 2147483647 else
                     f"""через {ttl_seconds} {'секунду' if ttl_seconds == 1 else
                                              'секунды' if ttl_seconds <= 4 else 'секунд'}""")
        caption = f"это {media_type} должно было исчезнуть {vanishing}, но я был быстрее и скачал его раньше"
    elif protected:
        caption = (f"{media_type} из секретного чата с {chat.username or chat.first_name}"
                   if isinstance(chat, User) else f"{media_type} из чата {chat.title}")

    if ttl_seconds or protected:
        from_user       : User    = await message.get_sender()
        media_file      : BytesIO = BytesIO()
        media_file.name : str     = get_file_name(media, media_type)
        force_document  : bool    = True if media_type == "документ" else False

        await client.download_media(media, media_file)
        media_file.seek(0)
        await client.send_file('me',
                               media_file,
                               caption=caption,
                               force_document=force_document,)
        await client.send_message("me",
                                  (f"отправитель: {from_user.username or from_user.first_name}\n"
                                   f"ID пользователя: {from_user.id}"),)
        
        del media_file # на всякий случай избавляемся от большого объекта в оперативной памяти. Garbage Collector, не благодари


client.start()
client.run_until_disconnected()
