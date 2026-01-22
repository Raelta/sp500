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
        Seeker -->|Apply Global Filters| PreProcess["Filter Data (Time/Day)"]
        PreProcess -->|Group by Structure| GridSplit[Split into Structural Combos]
        GridSplit -->|Distribute Tasks| Pool[ProcessPoolExecutor]
        
        %% Worker Layer
        subgraph "Worker Process (Parallel)"
            Pool -->|Bump Len, Slide Len| Calc[Rolling Calculations]
            Calc -->|Price Change, SizeVol| Metrics[Base Metrics]
            
            Metrics -->|Find Max Values| Pruning[Data-Driven Pruning]
            Pruning -->|Discard Impossible Thresholds| Masking[Boolean Mask Generation]
            
            Masking -->|Vectorize| MatrixBuild[Build Sparse Matrices]
            MatrixBuild -->|"Bump Matrix (N x B)"| DotProd[Matrix Multiplication]
            MatrixBuild -->|"Slide Matrix (N x S)"| DotProd
            
            DotProd -->|"Bump.T @ Slide"| Hits[Calculate Hits & Total Bumps]
            Hits -->|Compute %| CR[Conversion Rate]
            
            CR -->|Filter| ValidMask{Valid?}
            ValidMask -->|"CR >= Target"| OverlapFilter[Overlap Filtering (NMS)]
            OverlapFilter -->|Keep Best Slide| CleanHits[Recalculate CR]
            CleanHits -->|"CR >= Target"| Result[Store Result]
            ValidMask -->|Else| Discard[Discard]
        end
    end

    %% Output Layer
    Result -->|Collect| Aggregator[Result Aggregation]
    Aggregator -->|Sort by CR| Sorting
    Sorting -->|Top N| Console[Console Output]
    Sorting -->|All Results| CSV[CSV File]
```

## Optimized Catalog Search Flow

When using the `--use-catalog` flag, the process bypasses the rolling calculation step by using pre-computed matrices.

```mermaid
graph TD
    Start([User Command]) -->|Args: --use-catalog| CLI[goal_seek_cli.py]
    CLI -->|Load Catalog| Catalog[src/catalog.py]
    Catalog -->|Change Matrix (MemMap)| Memory
    Catalog -->|Metadata (RAM)| Memory
    
    CLI -->|Generate Grid| Searcher[CatalogSearcher]
    
    subgraph "Catalog Search Engine (src/catalog_search.py)"
        Searcher -->|Parallelize| Threads[ThreadPoolExecutor]
        
        subgraph "Thread Worker"
            Threads -->|Bump Len, Slide Len| Slicing[Array Slicing]
            Slicing -->|Fetch Change| MatrixLookup[Matrix Lookup]
            Slicing -->|Calc Vol/Up| CumSumDiff[CumSum Subtraction]
            
            CumSumDiff -->|Apply Filters| VectorFilter[Vectorized Filtering]
            VectorFilter -->|Filter Overlaps| NMS[Non-Maximum Suppression]
            NMS -->|Count Hits| Stats[Statistics]
        end
        
        Stats -->|Result| Collection
    end
    
    Collection --> Sorting
```

## Key Components

1.  **Window Catalog**: A pre-computed database of metrics.
    *   **Change Matrix**: 2GB Memory-mapped file storing % Change for every possible window size.
    *   **Cumulative Sums**: Small in-memory arrays allowing O(1) calculation of Volume and Up-Candle counts for any window.
2.  **Structural Grouping**: Parameters that require re-scanning the dataframe (Length) are grouped.
3.  **Data-Driven Pruning**: We check the maximum possible values in the actual dataset before testing thresholds. If the data only goes up to 5% change, we don't test a 6% threshold.
4.  **Vectorization**: Instead of looping through thresholds, we convert them into boolean matrices and use Linear Algebra (Matrix Multiplication) to count overlaps (Hits) instantly.
5.  **Overlap Filtering**: A post-processing step ensures that reported matches do not overlap in time. If multiple matches occur within overlapping windows, the one with the highest slide magnitude is preserved.
