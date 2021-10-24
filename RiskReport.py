import pandas as pd
import QuantLib as ql
import numpy as np


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
        df['Duration'] = ql.BondFunctions.duration(fixedRateBond, df.YTM, paymentConvention, ql.Compounded, frequency,
                                                   ql.Duration.Simple)
        df['DV01'] = df.Duration * cleanPrice / 10000
        df['AccuredInterest'] = fixedRateBond.accruedAmount(self.settlementDate)
        return df

    def getAggregateReport(self):
        df = self.portfolioAnalysis.copy()
        df['Maturity'] = df.MaturityDate.map(lambda x: x.year()) - df.IssueDate.map(lambda x: x.year())
        df = df[df.Maturity.isin(self.aggregateMaturity)]
        self.aggregateReport = df.groupby('Maturity')[['DV01', 'AccuredInterest', 'PositionNotional']].sum()

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

        df['Profit (Yield-)'] = np.round((df['Price+'] - df['Price']) * df['PositionNotional'], 3)
        df['Loss (Yield+)'] = np.round((df['Price-'] - df['Price']) * df['PositionNotional'], 3)
        return df[['Profit (Yield-)', 'Loss (Yield+)']]

    def printPortfolioReport(self):
        print('Aggregated DV01/Accrued interest/Notional:')
        output = self.aggregateReport.to_string(formatters={'DV01': "{:.3f}".format, \
                                                            'AccuredInterest': "{:.3%}".format})
        print(output)
        print('\n')
        print('Portfolio Pnl')
        print(self.pnlReport)


if __name__ == '__main__':
    B = BondPortfolio()
    B.loadData('sample_portfolio.csv')
    B.getPortfolioAnalysis()
    B.getAggregateReport()
    B.getPnl()
    B.printPortfolioReport()
