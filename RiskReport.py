import pandas as pd
import QuantLib as ql


class BondPortfolio:
    def __init__(self):
        self.settlementDate = ql.Date(12, 10, 2021)
        self.aggregateMaturity = [5, 10, 20, 30]
        self.yieldDelta = [5, 10, 15, 20, 25]
        self.dayCounter = ql.ActualActual()
        self.frequency = ql.Semiannual
        self.portfolio = None
        self.portfolioAnalysis = None
        self.aggregateReport = None
        self.pnlReport = None

    def loadData(self, filePath):
        usecols = ['SecurityID', 'IssueDate', 'FirstSettlementDate', 'AccrualDate',
                   'DaycountBasisType', 'CouponType', 'Coupon', 'FirstCouponDate',
                   'InterestPaymentFrequency', 'MaturityDate', 'Date',
                   'Price', ' PositionNotional ']
        dates = ['IssueDate', 'FirstSettlementDate', 'AccrualDate', 'FirstCouponDate', 'MaturityDate', 'Date']

        data = pd.read_csv(filePath, usecols=usecols, parse_dates=dates, thousands=',', index_col='SecurityID')
        data[dates] = data[dates].applymap(ql.Date().from_date)
        # data.DaycountBasisType = ql.ActualActual()
        # data.InterestPaymentFrequency = ql.Semiannual
        data = data.rename(columns={' PositionNotional ': 'PositionNotional'})
        self.portfolio = data

    def getPortfolioAnalysis(self):
        df = self.portfolio.copy()
        self.portfolioAnalysis = df.apply(self.getPortfolioAnalysisHelper, axis=1)

    def getPortfolioAnalysisHelper(self, df):
        startDate = df.IssueDate
        firstSettlementDate = df.FirstSettlementDate
        maturityDate = df.MaturityDate
        ql.Settings.instance().evaluationDate = df.Date
        settlementDays = firstSettlementDate - startDate

        frequency = self.frequency
        paymentConvention = self.dayCounter
        coupon = df.Coupon / 100
        face = 100
        cleanPrice = df.Price

        fixedRateBond = ql.FixedRateBond(settlementDays, ql.UnitedStates(), face, startDate, maturityDate,
                                         ql.Period(frequency), [coupon], paymentConvention)

        df['YTM'] = fixedRateBond.bondYield(cleanPrice, paymentConvention, ql.Compounded, frequency)
        df['Duration (Macaulay)'] = ql.BondFunctions.duration(fixedRateBond, df.YTM, paymentConvention, ql.Compounded,
                                                              frequency, ql.Duration.Macaulay)
        df['DV01'] = ql.BondFunctions.duration(fixedRateBond, df.YTM, paymentConvention, ql.Compounded, frequency,
                                               ql.Duration.Modified) * cleanPrice / 10000
        df['AccruedInterest (10/12/2021)'] = fixedRateBond.accruedAmount(self.settlementDate)
        return df

    def getAggregateReport(self):
        df = self.portfolioAnalysis.copy()
        df['Maturity'] = df.MaturityDate.map(lambda x: x.year()) - df.IssueDate.map(lambda x: x.year())
        df = df[df.Maturity.isin(self.aggregateMaturity)]
        df['Agg DV01'] = df['DV01'] * df['PositionNotional'] / 100
        df['Agg AccruedInterest (10/12/2021)'] = df['AccruedInterest (10/12/2021)'] * df['PositionNotional']
        self.aggregateReport = df.groupby('Maturity')[['Agg DV01', 'Agg AccruedInterest (10/12/2021)', 'PositionNotional']].sum()

    def getPnl(self):
        df = self.portfolioAnalysis.copy()
        pnlReport = pd.DataFrame()
        for d in self.yieldDelta:
            pnlReport[d] = df.apply(lambda x: self.getPnlHelper(x, d), axis=1).sum()
        pnlReport = pnlReport.T
        pnlReport.index.name = 'Yield Changes'
        self.pnlReport = pnlReport

    def getPnlHelper(self, df, delta):
        startDate = df.IssueDate
        firstSettlementDate = df.FirstSettlementDate
        maturityDate = df.MaturityDate
        ql.Settings.instance().evaluationDate = df.Date
        settlementDays = firstSettlementDate - startDate

        frequency = self.frequency
        paymentConvention = self.dayCounter
        coupon = df.Coupon / 100
        face = 100

        fixedRateBond = ql.FixedRateBond(settlementDays, ql.UnitedStates(), face, startDate, maturityDate,
                                         ql.Period(frequency), [coupon], paymentConvention)
        YTM = df['YTM'] - delta / 10000
        rate = ql.InterestRate(YTM, paymentConvention, ql.Compounded, frequency)
        df['Price+'] = ql.BondFunctions.cleanPrice(fixedRateBond, rate)
        YTM = df['YTM'] + delta / 10000
        rate = ql.InterestRate(YTM, paymentConvention, ql.Compounded, frequency)
        df['Price-'] = ql.BondFunctions.cleanPrice(fixedRateBond, rate)

        df['Profit (Yield-)'] = (df['Price+'] - df['Price']) * df['PositionNotional'] / 100
        df['Loss (Yield+)'] = (df['Price-'] - df['Price']) * df['PositionNotional'] / 100
        return df[['Profit (Yield-)', 'Loss (Yield+)']]

    def printPortfolioRiskReport(self):
        print('Aggregated DV01/Accrued interest/Notional:')
        print(self.aggregateReport)
        print('\n')
        print('Portfolio Pnl:')
        print(self.pnlReport)


if __name__ == '__main__':
    B = BondPortfolio()
    B.loadData('sample_portfolio.csv')
    # Step 1 Calculate YTM, Duration, DV01, Accrued Interest
    B.getPortfolioAnalysis()
    # Step 2 Aggregated DV01/Accrued interest/Notional on the maturity buckets: 5Y/10Y/20Y/30Y
    B.getAggregateReport()
    # Step 3 Calculate the portfolio profit and loss in 10 case scenarios, where yield is up/down 5,10,15,20,25  basis points
    B.getPnl()
    # Step 4 Print Result
    B.printPortfolioRiskReport()
