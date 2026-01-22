# Goal Seek Process Flow

This document outlines the architectural flow of the Goal Seek / Reverse Search engine.

```mermaid
graph TD
    %% CLI Layer
    Start([User Command]) -->|Args: Target CR, Ranges, Min Bumps| CLI[goal_seek_cli.py]
    CLI -->|Load Parquet| DataLoader[Data Loader]
    DataLoader -->|Clean & Validate| CLI
    CLI -->|Generate Grid| Seeker[GoalSeeker Engine]

    %% Search Engine Layer
    subgraph "Optimization Engine (src/search_engine.py)"
        Seeker -->|Apply Global Filters| PreProcess[Filter Data (Time/Day)]
        PreProcess -->|Group by Structure| GridSplit[Split into Structural Combos]
        GridSplit -->|Distribute Tasks| Pool[ProcessPoolExecutor]
        
        %% Worker Layer
        subgraph "Worker Process (Parallel)"
            Pool -->|Bump Len, Slide Len| Calc[Rolling Calculations]
            Calc -->|Price Change, SizeVol| Metrics[Base Metrics]
            
            Metrics -->|Find Max Values| Pruning[Data-Driven Pruning]
            Pruning -->|Discard Impossible Thresholds| Masking[Boolean Mask Generation]
            
            Masking -->|Vectorize| MatrixBuild[Build Sparse Matrices]
            MatrixBuild -->|Bump Matrix (N x B)| DotProd[Matrix Multiplication]
            MatrixBuild -->|Slide Matrix (N x S)| DotProd
            
            DotProd -->|Bump.T @ Slide| Hits[Calculate Hits & Total Bumps]
            Hits -->|Compute %| CR[Conversion Rate]
            
            CR -->|Filter| ValidMask{Valid?}
            ValidMask -->|CR >= Target| Result[Store Result]
            ValidMask -->|Bumps >= Min| Result
            ValidMask -->|Else| Discard[Discard]
        end
    end

    %% Output Layer
    Result -->|Collect| Aggregator[Result Aggregation]
    Aggregator -->|Sort by CR| Sorting
    Sorting -->|Top N| Console[Console Output]
    Sorting -->|All Results| CSV[CSV File]
```

## Key Components

1.  **Structural Grouping**: Parameters that require re-scanning the dataframe (Length) are grouped.
2.  **Data-Driven Pruning**: We check the maximum possible values in the actual dataset before testing thresholds. If the data only goes up to 5% change, we don't test a 6% threshold.
3.  **Vectorization**: Instead of looping through thresholds, we convert them into boolean matrices and use Linear Algebra (Matrix Multiplication) to count overlaps (Hits) instantly.
