from character_chat.engine import format_roleplay_reply


def test_roleplay_reply_decodes_escaped_newlines_and_removes_orphan_star():
    assert format_roleplay_reply('*\\n\\n"Còn đứng đó làm gì?"') == '"Còn đứng đó làm gì?"'


def test_roleplay_reply_separates_single_or_double_star_action_from_dialogue():
    assert format_roleplay_reply('*nhìn anh* "Đi thôi."') == '**nhìn anh**\n"Đi thôi."'
    assert format_roleplay_reply('**nhìn anh** "Đi thôi."') == '**nhìn anh**\n"Đi thôi."'
