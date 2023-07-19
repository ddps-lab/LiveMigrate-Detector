import GspreadUtils
import Transferable

df = GspreadUtils.read_gspread('mat_mul(r4.large)')
df = df.drop('instance groups', axis=1)

GROUP_NUMBER = df.shape[0]
Transferable.Digraph(GROUP_NUMBER, df)