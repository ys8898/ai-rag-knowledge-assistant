def calculate_confidence(results):

    if not results:
        return {
            "score":0,
            "level":"low"
        }


    top_score = results[0]["rerank_score"]


    if len(results) > 1:

        second_score = results[1]["rerank_score"]

        margin = top_score - second_score

    else:

        margin = 10



    # 分差
    if margin > 2:
        margin_score = 1

    elif margin > 0.8:
        margin_score = 0.5

    else:
        margin_score = 0.2



    # top分数
    # 不判断正负，只看是否最高
    if top_score > -1:
        score_score = 1

    elif top_score > -3:
        score_score = 0.6

    else:
        score_score = 0.3



    final_score = (
        margin_score * 0.6
        +
        score_score * 0.4
    )


    if final_score >=0.7:

        level="high"

    elif final_score>=0.4:

        level="medium"

    else:

        level="low"


    return {
        "score":round(final_score,2),
        "level":level
    }