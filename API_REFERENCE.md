# LinkedIn Pages Data Portability API — Endpoint Reference

Product version: **202604**.

All endpoints require the **`r_dma_admin_pages_content`** OAuth scope and a 3-legged member access token.
Base URL: `https://api.linkedin.com`

Total endpoint entries: **142** across **31** logical groups.

## Table of contents

- [Feed — Posts & Reposts](#feed-posts-reposts) — 4 entries
- [Feed — Engagement](#feed-engagement) — 5 entries
- [Feed — Content Finder](#feed-content-finder) — 6 entries
- [Feed — Featured Content](#feed-featured-content) — 3 entries
- [Feed — Page Credibility](#feed-page-credibility) — 3 entries
- [Feed — Content Ingestion Sources](#feed-content-ingestion-sources) — 1 entries
- [Pages Follows](#pages-follows) — 2 entries
- [Pages Profiles](#pages-profiles) — 9 entries
- [Pages Lookup](#pages-lookup) — 1 entries
- [Analytics — Content](#analytics-content) — 3 entries
- [Analytics — Edge (followers/visitors)](#analytics-edge-followers-visitors) — 2 entries
- [Analytics — Visitor of the Day](#analytics-visitor-of-the-day) — 1 entries
- [Analytics — Creator](#analytics-creator) — 1 entries
- [Notifications](#notifications) — 1 entries
- [Lead Gen — Forms](#lead-gen-forms) — 4 entries
- [Lead Gen — Analytics](#lead-gen-analytics) — 1 entries
- [Messaging](#messaging) — 2 entries
- [Events](#events) — 4 entries
- [Live Videos](#live-videos) — 3 entries
- [Publishing](#publishing) — 8 entries
- [Products](#products) — 7 entries
- [Services](#services) — 2 entries
- [Employer Brand & Life Page](#employer-brand-life-page) — 23 entries
- [Business Manager](#business-manager) — 3 entries
- [Identity](#identity) — 3 entries
- [Settings — Access Control](#settings-access-control) — 2 entries
- [Settings — Authorizations](#settings-authorizations) — 3 entries
- [Settings — Email Domain Mapping](#settings-email-domain-mapping) — 1 entries
- [Verification Agent](#verification-agent) — 2 entries
- [Activities](#activities) — 1 entries
- [Standardized Data](#standardized-data) — 31 entries

## Feed — Posts & Reposts

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaInstantReposts` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaInstantReposts` | FINDER | author | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaInstantReposts` | FINDER | repostedContent | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaPosts` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Feed — Engagement

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaComments` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaContentPublicUrl` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaIngestedContentSummaries` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaReactions` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaSocialMetadata` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Feed — Content Finder

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaFeedContentsExternal` | FINDER | commentsOnEntity | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFeedContentsExternal` | FINDER | postsByAuthor | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFeedContentsExternal` | FINDER | reactionsOnEntity | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFeedContentsExternal` | FINDER | repostsByReposter | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFeedContentsExternal` | FINDER | repostsFromEntity | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFeedContentsExternal` | FINDER | resharesFromEntity | `r_dma_admin_pages_content` | Member (3-legged) |

## Feed — Featured Content

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaPagesFeaturedContentGroups` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaPagesFeaturedContentGroups` | FINDER | page | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaPagesFeaturedContentGroups/{key}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Feed — Page Credibility

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationalPageCredibility` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationalPageCredibility` | FINDER | page | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationalPageCredibility/{key}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Feed — Content Ingestion Sources

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationalPageContentIngestionSources` | FINDER | organizationalPage | `r_dma_admin_pages_content` | Member (3-legged) |

## Pages Follows

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationalPageFollows` | FINDER | followee | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationalPageFollows` | FINDER | follower | `r_dma_admin_pages_content` | Member (3-legged) |

## Pages Profiles

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationSearchAppearance` | FINDER | organization | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationalPageProfiles` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationalPageProfiles` | FINDER | pageEntity | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationalPageProfiles/{organizationalPageUrn}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizations` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizations` | FINDER | emailDomain | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizations` | FINDER | parentOrganization | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizations` | FINDER | vanityName | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizations/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Pages Lookup

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationLookup` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Analytics — Content

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationalPageContentAnalytics` | FINDER | postDimension | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationalPageContentAnalytics` | FINDER | postGestures | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationalPageContentAnalytics` | FINDER | trend | `r_dma_admin_pages_content` | Member (3-legged) |

## Analytics — Edge (followers/visitors)

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationalPageEdgeAnalytics` | FINDER | dimension | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationalPageEdgeAnalytics` | FINDER | trend | `r_dma_admin_pages_content` | Member (3-legged) |

## Analytics — Visitor of the Day

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationalPageVisitorOfTheDay` | FINDER | organizationalPage | `r_dma_admin_pages_content` | Member (3-legged) |

## Analytics — Creator

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaCreatorAnalytics` | FINDER | targetEntity | `r_dma_admin_pages_content` | Member (3-legged) |

## Notifications

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationalPageNotifications` | FINDER | organizationalPage | `r_dma_admin_pages_content` | Member (3-legged) |

## Lead Gen — Forms

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaLeadGenForm` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaLeadGenForm` | FINDER | owner | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaLeadGenForm/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaLeadGenFormResponse` | FINDER | owner | `r_dma_admin_pages_content` | Member (3-legged) |

## Lead Gen — Analytics

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaLeadAnalytics` | FINDER | owner | `r_dma_admin_pages_content` | Member (3-legged) |

## Messaging

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaPageMessagingMessages` | FINDER | thread | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaPageMessagingThreads` | FINDER | pageMailboxOwner | `r_dma_admin_pages_content` | Member (3-legged) |

## Events

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaEventRoleAssignments` | FINDER | event | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaEvents` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaEvents` | FINDER | organizer | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaEvents/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Live Videos

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaLiveVideos` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaLiveVideos/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaLiveViewerCountAnalytics` | FINDER | statistics | `r_dma_admin_pages_content` | Member (3-legged) |

## Publishing

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaContentSeries` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaContentSeries` | FINDER | owner | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaContentSeries/{key}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOriginalArticles` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOriginalArticles` | FINDER | author | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOriginalArticles` | FINDER | permlink | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOriginalArticles/{key}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaSeriesSubscribers` | FINDER | contentSeries | `r_dma_admin_pages_content` | Member (3-legged) |

## Products

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationProducts` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationProducts` | FINDER | organization | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationProducts` | FINDER | organizationalPage | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationProducts` | FINDER | vanityName | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationProducts/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaProductCategories` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaProductCategories/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Services

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationServicesPageEngagements` | FINDER | organization | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationServicesPageProviders` | FINDER | organization | `r_dma_admin_pages_content` | Member (3-legged) |

## Employer Brand & Life Page

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaAdminContentMediaGallery` | FINDER | organization | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaCareerPageSettings/{organization}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaEmployeeBroadcastAnalytics` | FINDER | topEmployeeBroadcasts | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaEmployeeBroadcastAudienceDemographicAnalytics` | FINDER | organizationalPage | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaEmployeeBroadcastAudienceTimeSeriesAnalytics` | FINDER | organizationalPage | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaEmployeeBroadcastHighlights` | FINDER | organizationalPage | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationCommitment` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationCommitment` | FINDER | organization | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationCommitment/{organizationCommitmentUrn}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationContentRevisions` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationContentRevisions` | FINDER | history | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationContentRevisions` | FINDER | published | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationContentRevisions/{organizationContentRevisionUrn}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationLifePageTrafficStatistics` | FINDER | organization | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationPhotos` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationPhotos` | FINDER | organization | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationPhotos/{organizationPhotoUrn}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationRelationshipStatistics` | FINDER | statisticSortType | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationTargetedContents` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationTargetedContents/{organizationTargetedContentUrn}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationWorkplacePolicies` | FINDER | organization | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationWorkplacePolicies/{organizationWorkplacePolicyUrn}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaTalentBrandAnalyticSummaries` | FINDER | organizationAndTimeRange | `r_dma_admin_pages_content` | Member (3-legged) |

## Business Manager

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaBusinessManagerAccountOrganizations` | BATCH_FINDER | organizations | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaBusinessManagerAccounts` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaBusinessManagerAccounts/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Identity

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaMe` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaPeople` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaPeople/{personId}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Settings — Access Control

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationAcls` | FINDER | organization | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationAcls` | FINDER | roleAssignee | `r_dma_admin_pages_content` | Member (3-legged) |

## Settings — Authorizations

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationAuthorizations` | BATCH_FINDER | authorizationActionsAndImpersonator | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationAuthorizations` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaOrganizationAuthorizations/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Settings — Email Domain Mapping

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaOrganizationalPageEmailDomainMapping` | FINDER | organizationalPageAndUseCase | `r_dma_admin_pages_content` | Member (3-legged) |

## Verification Agent

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaVerificationAgents` | FINDER | organizationalPage | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaVerificationAgents` | FINDER | workEmailDomain | `r_dma_admin_pages_content` | Member (3-legged) |

## Activities

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaActivities` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |

## Standardized Data

| Resource | Method | Finder / Sub-action | Scope | Auth |
| --- | --- | --- | --- | --- |
| `/rest/dmaBenefitTaxonomyVersions/{version}/dmaBenefits` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaBenefitTaxonomyVersions/{version}/dmaBenefits/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaDegrees` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaDegrees` | GET_ALL | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaDegrees/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFeaturedCommitmentTaxonomyVersions/{version}/dmaFeaturedCommitment` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFeaturedCommitmentTaxonomyVersions/{version}/dmaFeaturedCommitment/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFieldsOfStudy` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFieldsOfStudy` | GET_ALL | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFieldsOfStudy/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFunctions` | GET_ALL | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaFunctions/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaGeo` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaGeo/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaIndustryTaxonomyVersions/{version}/dmaIndustries` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaIndustryTaxonomyVersions/{version}/dmaIndustries` | GET_ALL | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaIndustryTaxonomyVersions/{version}/dmaIndustries/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaSkills` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaSkills` | GET_ALL | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaSkills/{skillId}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaStandardizedIndustries` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaStandardizedIndustries` | GET_ALL | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaStandardizedIndustries/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaStandardizedSeniorities` | GET_ALL | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaStandardizedSeniorities/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaSuperTitles` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaSuperTitles` | GET_ALL | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaSuperTitles/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaTitles` | BATCH_GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaTitles` | GET_ALL | — | `r_dma_admin_pages_content` | Member (3-legged) |
| `/rest/dmaTitles/{id}` | GET | — | `r_dma_admin_pages_content` | Member (3-legged) |
