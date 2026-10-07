from backend import notebook_logic as l
print(l.df[['번호','subject','데이터역할']].head(30).to_string(index=False))
