# GitHub Actions Setup for IV Collection

This guide explains how to set up GitHub Actions for automated IV data collection in the cloud.

## Overview

GitHub Actions will run your IV collection scripts on schedule, ensuring data is collected even when your computer is off. The workflows run on GitHub's servers and are completely free for public repositories (2000 minutes/month for private repos).

## Required GitHub Secrets

You need to add the following secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret" and add each of these:

### Required Secrets:
- `ALPACA_API_KEY` - Your Alpaca API key
- `ALPACA_SECRET_KEY` - Your Alpaca secret key
- `POLYGON_API_KEY` - Your Polygon.io API key (if you have one)
- `GEMINI_API_KEY` - Your Google Gemini API key
- `ANTHROPIC_API_KEY` - Your Anthropic API key

### How to find your API keys:
- **Alpaca**: https://app.alpaca.markets/paper/dashboard/overview (click "View" under API Keys)
- **Polygon**: https://polygon.io/dashboard/api-keys
- **Gemini**: https://makersuite.google.com/app/apikey
- **Anthropic**: https://console.anthropic.com/settings/keys

## Workflow Schedule

The GitHub Actions are configured to run:

1. **Daily IV Collection**: 6:30 PM ET on weekdays
2. **Intraday IV Collection**: Every 30 minutes from 9:00 AM to 3:30 PM ET on weekdays
3. **Weekly Maintenance**:
   - Backfill missing data: Sundays at 10:00 AM ET
   - Recalculate IV ranks: Sundays at 11:00 AM ET

## Manual Triggers

You can manually trigger any workflow:
1. Go to Actions tab in your GitHub repository
2. Select the workflow you want to run
3. Click "Run workflow"
4. Select the branch and click "Run workflow"

## Monitoring

To monitor your workflows:
1. Go to the Actions tab in your repository
2. Click on a workflow run to see details
3. Download artifacts (logs) from completed runs

## Timezone Notes

- GitHub Actions uses UTC time
- The cron schedules are adjusted for Eastern Time
- During EDT (summer): ET = UTC - 4 hours
- During EST (winter): ET = UTC - 5 hours

## Troubleshooting

### Workflow not running?
- Check if secrets are properly set
- Verify the workflow files are in `.github/workflows/`
- Check the Actions tab for error messages

### Scripts failing?
- Download the log artifacts to see detailed error messages
- Ensure all dependencies are in `requirements.txt`
- Check that database files are committed to the repository

### Data not updating?
- Verify API keys are valid and have necessary permissions
- Check if the data sources (Alpaca, Polygon) are accessible
- Review the logs for specific error messages

## Cost

- **Public repositories**: Unlimited free minutes
- **Private repositories**: 2000 free minutes/month
- Our usage: ~30 minutes/day = ~900 minutes/month (well within free tier)

## Next Steps

After setting up the secrets, the workflows will automatically start running on schedule. You can also trigger them manually to test that everything is working correctly.