# Question Generation Quality Improvements

*Date: 2025-07-10*

## Example Problems from Generated Questions

```json
{
  "question": "说到参与财富存量分配，作者如何将自己的做法与巴菲特相比较？",
  "answer": "巴菲特是用钱去参与，我们用人参与，本质上都一样，你买股票，我把儿子嫁过去，这都是参与财富存量分配"
}

{
  "question": "这东西是谁创造的？",
  "answer": "索罗斯那批人，本森特那批人"
}
```

**Problems Identified:**
1. **Overly specific questions** that unlikely to be asked by human users
2. **Vague pronouns** ("这东西") without context
3. **Unnatural phrasing** that sounds academic rather than conversational
4. **Context dependency** - questions only make sense with the specific chunk

## Solutions
- Prompt improvement: more instructions, add metadata, add previous_chunk, add one-shot example